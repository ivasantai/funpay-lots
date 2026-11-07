"""Функции поверх клиента FunPay: статистика продаж, цены конкурентов, аренды, бэкап лотов."""
from __future__ import annotations

import datetime as dt
import re
import statistics
import time

from funpay_client import FunPayClient, FunPayError, SYSTEM_FIELDS, parse_duration

# ---------- статистика ----------

def _num(s: str) -> float:
    try:
        return float(re.sub(r"[^\d.,-]", "", s or "").replace(",", ".") or 0)
    except ValueError:
        return 0.0


def short_title(title: str) -> str:
    """«⚡ ... АРЕНДА 💎, С подпиской, Pro» → без хвоста с параметрами раздела, который FunPay дописывает через запятую."""
    return re.sub(r"(,\s*[^,]{1,30})+$", "", title or "").strip() or title


def collect_orders(client: FunPayClient, since_ts: int, max_pages: int = 15) -> list[dict]:
    items, cont = [], ""
    for _ in range(max_pages):
        page = client.orders(cont)
        items += page["items"]
        cont = page["next"]
        if not cont or not page["items"] or (page["items"][-1]["ts"] and page["items"][-1]["ts"] < since_ts):
            break
    return [i for i in items if i["ts"] >= since_ts]


def stats(client: FunPayClient, days: int = 30) -> dict:
    days = max(1, min(int(days), 365))
    now = dt.datetime.now()
    start = (now - dt.timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    orders = collect_orders(client, int(start.timestamp()))
    by_day: dict[str, dict] = {}
    for i in range(days):
        d = (start + dt.timedelta(days=i)).strftime("%Y-%m-%d")
        by_day[d] = {"date": d, "revenue": {}, "orders": 0, "refunds": 0}
    lots: dict[str, dict] = {}
    totals = {"revenue": {}, "orders": 0, "refunds": 0, "refund_sum": {}}
    buyers: dict[str, int] = {}
    for o in orders:
        day = dt.datetime.fromtimestamp(o["ts"]).strftime("%Y-%m-%d")
        bucket = by_day.get(day)
        amount, unit = _num(o["amount"]), o["unit"] or "$"
        if o["status"] == "refunded":
            totals["refunds"] += 1
            totals["refund_sum"][unit] = round(totals["refund_sum"].get(unit, 0) + amount, 2)
            if bucket:
                bucket["refunds"] += 1
            continue
        totals["orders"] += 1
        totals["revenue"][unit] = round(totals["revenue"].get(unit, 0) + amount, 2)
        if bucket:
            bucket["orders"] += 1
            bucket["revenue"][unit] = round(bucket["revenue"].get(unit, 0) + amount, 2)
        key = short_title(o["title"])
        lot = lots.setdefault(key, {"title": key, "orders": 0, "revenue": {}, "category": o["category"]})
        lot["orders"] += 1
        lot["revenue"][unit] = round(lot["revenue"].get(unit, 0) + amount, 2)
        buyers[o["buyer"]] = buyers.get(o["buyer"], 0) + 1
    main_unit = max(totals["revenue"], key=lambda u: totals["revenue"][u], default="$")
    avg = round(totals["revenue"].get(main_unit, 0) / totals["orders"], 2) if totals["orders"] else 0
    top = sorted(lots.values(), key=lambda x: (-x["revenue"].get(main_unit, 0), -x["orders"]))
    return {
        "days": days, "unit": main_unit, "totals": totals, "avg": avg,
        "repeat_buyers": sum(1 for v in buyers.values() if v > 1), "buyers": len(buyers),
        "by_day": list(by_day.values()), "top": top[:15],
    }


# ---------- конкуренты ----------

def competitors(client: FunPayClient, node: int) -> dict:
    _, my_lots = client.category_lots(int(node))
    mine_ids = {l["id"] for l in my_lots}
    pub = client.public_offers(int(node), mine_ids)
    offers = pub["offers"]
    by_id = {o["id"]: o for o in offers}
    rows = []
    for lot in my_lots:
        me = by_id.get(lot["id"])
        minutes = parse_duration(lot["title"])
        if not me:
            # Лот выключен (или скрыт) — на витрине его нет; показываем рынок для того же срока.
            same = [o for o in offers if not o["mine"] and minutes is not None and o["minutes"] == minutes]
            prices = sorted(o["price"] for o in same)
            rows.append({"id": lot["id"], "title": lot["title"], "visible": False, "active": lot["active"],
                         "minutes": minutes, "my_price": None, "seller_price": lot["price"], "unit": lot["unit"],
                         "rivals": len(prices), "rank": None,
                         "min": prices[0] if prices else None,
                         "median": round(statistics.median(prices), 2) if prices else None,
                         "cheaper_online": None, "cheapest": sorted(same, key=lambda o: o["price"])[:5]})
            continue
        # Сравниваем с похожими: те же фильтры раздела и (если удалось распознать) тот же срок.
        same = [o for o in offers if not o["mine"] and o["filters"] == me["filters"]
                and (minutes is None or o["minutes"] == minutes)]
        prices = sorted(o["price"] for o in same)
        cheaper = sum(1 for p in prices if p < me["price"])
        rows.append({
            "id": lot["id"], "title": lot["title"], "visible": True, "minutes": minutes,
            "my_price": me["price"], "unit": me["unit"], "filters": me["filters"],
            "rivals": len(prices), "rank": cheaper + 1,
            "min": prices[0] if prices else None,
            "median": round(statistics.median(prices), 2) if prices else None,
            "cheaper_online": sum(1 for o in same if o["price"] < me["price"] and o["online"]),
            "cheapest": sorted(same, key=lambda o: o["price"])[:5],
        })
    rows.sort(key=lambda r: (not r["visible"], r["title"]))
    return {"node": int(node), "total_offers": len(offers), "rows": rows}


# ---------- аренды ----------

def rentals(orders: list[dict], now: float | None = None, bonus_minutes: int = 0) -> list[dict]:
    """Активные и недавно закончившиеся аренды по заказам: срок берётся из названия лота («НА 3 ЧАСА»)."""
    now = now or time.time()
    out = []
    for o in orders:
        if o["status"] == "refunded" or not o["ts"]:
            continue
        minutes = parse_duration(o["title"])
        if not minutes or minutes > 60 * 24 * 7:  # месячные подписки — не аренда на часы
            continue
        end = o["ts"] + (minutes + bonus_minutes) * 60
        if end < now - 6 * 3600:
            continue
        out.append({**o, "minutes": minutes, "end": end, "left": int(end - now), "active": end > now})
    out.sort(key=lambda r: r["end"])
    return out


# ---------- бэкап ----------

def backup_lot(client: FunPayClient, node: int, offer: int, category: str) -> dict:
    form = client.get_form(node, offer)
    fields = {}
    for f in form["fields"]:
        if f["kind"] == "system":
            continue
        fields[f["name"]] = f["value"]
    title = fields.get("fields[summary][ru]", "") or ""
    return {"node": node, "offer": offer, "category": category, "title": title, "fields": fields}


def restore_lot(client: FunPayClient, item: dict, inactive: bool = True) -> dict:
    """Создаёт НОВЫЙ лот из записи бэкапа (старый лот не трогается)."""
    node = int(item["node"])
    form = client.get_form(node)
    saved = item.get("fields") or {}
    known = set()
    for f in form["fields"]:
        if f["kind"] == "system":
            continue
        known.add(f["name"])
        if f["name"] in saved:
            f["value"] = saved[f["name"]]
        if f["name"] == "active" and inactive:
            f["value"] = False
    missing = [k for k in saved if k not in known and k not in SYSTEM_FIELDS]
    client.save(form["fields"])
    return {"done": True, "skipped_fields": missing}


def check_backup(data: dict) -> list[dict]:
    if not isinstance(data, dict) or data.get("app") != "FunPay Lots" or not isinstance(data.get("lots"), list):
        raise FunPayError("Это не файл бэкапа FunPay Lots.")
    return data["lots"]
