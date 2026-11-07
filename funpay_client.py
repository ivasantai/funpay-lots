"""Мини-клиент FunPay для управления своими лотами.

Официального API у FunPay нет, поэтому авторизация идёт через cookie `golden_key`
(тот самый «ключ» аккаунта), а работа — через те же запросы, что делает сайт.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

BASE = "https://funpay.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT = 25
# Служебные поля формы: не показываем пользователю, но отправляем обратно.
SYSTEM_FIELDS = {"csrf_token", "form_created_at", "offer_id", "node_id", "location", "deleted"}


class FunPayError(Exception):
    pass


@dataclass
class Account:
    id: int
    username: str
    balance: str = ""
    csrf: str = ""


@dataclass
class Category:
    node: int
    name: str
    lots: list = field(default_factory=list)


def _text(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


class FunPayClient:
    def __init__(self, golden_key: str):
        golden_key = (golden_key or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9]{16,64}", golden_key):
            raise FunPayError("Ключ выглядит неверно: golden_key — это строка из латиницы и цифр (обычно 32 символа).")
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Language": "ru,en;q=0.8"})
        self.s.cookies.set("golden_key", golden_key, domain="funpay.com")
        self.account: Account | None = None
        self._games: list[dict] | None = None
        self.node_games: dict[int, int] = {}  # раздел -> игра (нужно для поднятия)

    # ---------- низкоуровневое ----------
    def _get(self, path: str, **kw) -> requests.Response:
        try:
            r = self.s.get(path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}", timeout=TIMEOUT, **kw)
        except requests.RequestException as e:
            raise FunPayError(f"Нет связи с FunPay: {e}") from e
        if r.status_code == 403:
            raise FunPayError("FunPay отклонил запрос (403). Возможно, ключ устарел — зайдите на сайт и возьмите новый golden_key.")
        if r.status_code >= 400:
            raise FunPayError(f"FunPay вернул ошибку {r.status_code} на {path}")
        return r

    def _post(self, path: str, data: list[tuple[str, str]], labels: dict | None = None) -> dict:
        labels = labels or {}
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "x-requested-with": "XMLHttpRequest",
            "origin": BASE,
            "referer": f"{BASE}/lots/offerEdit",
        }
        try:
            r = self.s.post(f"{BASE}/{path}", data=data, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise FunPayError(f"Нет связи с FunPay: {e}") from e
        try:
            js = r.json()
        except ValueError:
            raise FunPayError(f"Неожиданный ответ FunPay ({r.status_code}): {r.text[:200]}")
        if js.get("error") or js.get("errors"):
            msgs = []
            if isinstance(js.get("error"), str) and js["error"]:
                msgs.append(js["error"])
            errs = js.get("errors")
            pairs = list(errs.items()) if isinstance(errs, dict) else (errs if isinstance(errs, list) else [])
            for e in pairs:
                if isinstance(e, (list, tuple)) and len(e) >= 2:
                    msgs.append(f"{labels.get(e[0], e[0])}: {e[1]}")
                else:
                    msgs.append(str(e))
            raise FunPayError(" • ".join(m.rstrip(".") for m in msgs) or "FunPay отклонил сохранение")
        return js

    # ---------- аккаунт ----------
    def login(self) -> Account:
        r = self._get("/")
        bs = BeautifulSoup(r.text, "html.parser")
        body = bs.find("body")
        try:
            app = json.loads(body["data-app-data"])
        except Exception:
            raise FunPayError("Не удалось прочитать страницу FunPay — возможно, сайт изменился.")
        uid = app.get("userId")
        if not uid:
            raise FunPayError("Ключ не подошёл: FunPay не узнал аккаунт. Проверьте golden_key.")
        name = _text(bs.select_one(".user-link-name")) or f"id {uid}"
        bal = _text(bs.select_one(".badge-balance"))
        self.account = Account(int(uid), name, bal, app.get("csrf-token", ""))
        self._games = self._parse_games(bs)
        return self.account

    def _need_login(self):
        if not self.account:
            self.login()

    @staticmethod
    def _parse_games(bs: BeautifulSoup) -> list[dict]:
        """Каталог игр/разделов с главной страницы (только обычные лоты, без валюты)."""
        games, seen = [], set()
        for item in bs.select(".promo-game-item"):
            title = item.select_one(".game-title")
            gname = _text(title)
            subs = []
            for a in item.select("li a[href]"):
                m = re.search(r"/lots/(\d+)/", a["href"])
                if m and int(m.group(1)) not in seen:
                    seen.add(int(m.group(1)))
                    subs.append({"node": int(m.group(1)), "name": _text(a)})
            if gname and subs:
                games.append({"game": gname, "subs": subs})
        return games

    def games(self) -> list[dict]:
        self._need_login()
        return self._games or []

    # ---------- лоты ----------
    def profile_categories(self) -> dict[int, str]:
        """Разделы, в которых у аккаунта есть активные лоты (по странице профиля)."""
        self._need_login()
        r = self._get(f"users/{self.account.id}/")
        bs = BeautifulSoup(r.text, "html.parser")
        cats: dict[int, str] = {}
        for t in bs.select(".offer-list-title"):
            a = t.select_one('a[href*="/lots/"]')
            m = a and re.search(r"/lots/(\d+)/", a["href"])
            if m:
                cats[int(m.group(1))] = _text(t)
        return cats

    def category_lots(self, node: int) -> tuple[str, list[dict]]:
        """Все свои лоты в разделе, включая неактивные (страница «Ваши предложения»)."""
        r = self._get(f"lots/{node}/trade")
        bs = BeautifulSoup(r.text, "html.parser")
        if not bs.select_one('a[href*="offerEdit"]'):
            raise FunPayError(f"Раздел {node} не найден или недоступен для продажи.")
        raise_btn = bs.select_one(".js-lot-raise[data-game]")
        if raise_btn:
            self.node_games[node] = int(raise_btn["data-game"])
        # Заголовок страницы — «Ваши предложения»; название раздела берём из ссылки «Назад»/хлебных крошек.
        name = ""
        back = bs.select_one(f'a[href$="/lots/{node}/"]')
        if back and _text(back) and _text(back).lower() != "назад":
            name = _text(back)
        lots = []
        for a in bs.select("a.tc-item"):
            m = re.search(r"offer=(\d+)", a.get("href", ""))
            if not m:
                continue
            price_el = a.select_one(".tc-price")
            unit = _text(price_el.select_one(".unit")) if price_el else ""
            # Видимая цена (как на сайте); data-s — машинное значение для сортировки, бывает с лишними знаками.
            price = _text(price_el).replace(unit, "").strip() if price_el else ""
            if not price and price_el:
                price = price_el.get("data-s", "")
            server = _text(a.select_one(".tc-server"))
            classes = a.get("class", [])
            lots.append({
                "id": int(m.group(1)),
                "node": node,
                "title": _text(a.select_one(".tc-desc-text")) or _text(a.select_one(".tc-desc")),
                "server": server,
                "amount": _text(a.select_one(".tc-amount")),
                "price": price,
                "unit": unit,
                "active": "warning" not in classes and "inactive" not in classes,
            })
        return name, lots

    # ---------- форма лота ----------
    def get_form(self, node: int, offer: int | None = None) -> dict:
        path = f"lots/offerEdit?node={node}" + (f"&offer={offer}" if offer else "")
        r = self._get(path)
        bs = BeautifulSoup(r.text, "html.parser")
        form = bs.find("form", action=re.compile(r"offerSave"))
        if not form:
            raise FunPayError("FunPay не отдал форму лота (лот удалён или нет доступа к разделу).")
        fields = []
        for el in form.find_all(["input", "select", "textarea"]):
            name = el.get("name")
            if not name:
                continue
            grp = el.find_parent(class_="form-group")
            gcls = grp.get("class", []) if grp else []
            label_el = grp.find("label", class_="control-label") if grp else None
            label = _text(label_el)
            if not label and el.get("type") == "checkbox":
                label = _text(el.find_parent("label"))
            locale = grp.get("data-locale") if grp else None
            f = {
                "name": name,
                "label": label or name,
                "locale": locale or "",
                "conditional": bool(grp and "lot-field" in gcls and "hidden" in gcls and not locale),
            }
            if el.name == "select":
                opts = [{"value": o.get("value", ""), "text": _text(o)} for o in el.find_all("option")]
                sel = el.find("option", selected=True)
                f.update(kind="select", options=opts, value=sel.get("value", "") if sel else "")
            elif el.name == "textarea":
                f.update(kind="textarea", value=el.text or "")
            elif el.get("type") == "checkbox":
                f.update(kind="checkbox", value=el.has_attr("checked"))
            elif el.get("type") == "hidden":
                f.update(kind="system" if name in SYSTEM_FIELDS else "hidden", value=el.get("value", ""))
            else:
                f.update(kind="text", value=el.get("value", ""))
            fields.append(f)
        title = _text(bs.select_one("h1"))
        return {"node": node, "offer": offer or 0, "title": title, "fields": fields}

    def save(self, fields: list[dict]) -> dict:
        """Отправляет форму. fields — список из get_form с изменёнными value."""
        data: list[tuple[str, str]] = []
        for f in fields:
            if f["kind"] == "checkbox":
                if f.get("value"):
                    data.append((f["name"], "on"))
            else:
                v = f.get("value")
                data.append((f["name"], "" if v is None else str(v)))
        names = {n for n, _ in data}
        if "location" in names:
            data = [(n, "trade" if n == "location" else v) for n, v in data]
        else:
            data.append(("location", "trade"))
        labels = {f["name"]: f.get("label") or f["name"] for f in fields}
        return self._post("lots/offerSave", data, labels)

    def _modify(self, node: int, offer: int, changes: dict) -> dict:
        form = self.get_form(node, offer)
        for f in form["fields"]:
            if f["name"] in changes:
                f["value"] = changes[f["name"]]
        return self.save(form["fields"])

    # ---------- финансы ----------
    def _xhr(self, path: str, data: dict) -> requests.Response:
        headers = {"accept": "*/*", "x-requested-with": "XMLHttpRequest", "origin": BASE,
                   "referer": f"{BASE}/account/balance"}
        try:
            r = self.s.post(f"{BASE}/{path}", data=data, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise FunPayError(f"Нет связи с FunPay: {e}") from e
        if r.status_code >= 400:
            raise FunPayError(f"FunPay вернул ошибку {r.status_code} на {path}")
        return r

    def finance(self) -> dict:
        """Балансы, способы вывода (с комиссиями и сохранёнными кошельками) и фильтры истории."""
        self._need_login()
        bs = BeautifulSoup(self._get("account/balance").text, "html.parser")
        form = bs.find("form", action=re.compile(r"withdraw/withdraw"))
        box = bs.select_one(".withdraw-box")
        if not form or not box:
            raise FunPayError("Не удалось прочитать страницу «Финансы» — возможно, FunPay изменил сайт.")
        self._wd_csrf = form.select_one("[name=csrf_token]")["value"]
        cfg = json.loads(box["data-data"])

        balances = []
        for o in form.select('select[name="currency_id"] option'):
            content = BeautifulSoup(o.get("data-content", ""), "html.parser")
            cur = cfg["currencies"].get(o["value"], {})
            balances.append({
                "id": o["value"],
                "name": _text(content.select_one(".payment-title")) or cur.get("name", o["value"]),
                "value": _text(content.select_one(".payment-value")),
                "unit": cur.get("unit", ""),
                "channels": [{"id": ch["extCurrency"], "name": ch["name"], "fee": ch.get("feeInfo", "")}
                             for ch in cur.get("channels", [])],
            })
        ext = {k: {"name": v.get("name", k), "unit": v.get("unit", ""), "wallet_name": v.get("walletName", "Кошелёк"),
                   "wallets": v.get("wallets") or []} for k, v in cfg["extCurrencies"].items()}
        banks = []
        for o in form.select('select[name="wallet_extra"] option'):
            if o.get("value"):
                banks.append({"id": o["value"], "name": _text(BeautifulSoup(o.get("data-content", ""), "html.parser")) or o["value"]})
        filters = [{"id": a.get("data-value", ""), "name": _text(a)} for a in bs.select(".dyn-table-filter [data-value]")]
        if not filters:
            filters = [{"id": "", "name": "Все операции"}]
        return {"balances": balances, "ext": ext, "banks": banks, "filters": filters}

    def transactions(self, filter_: str = "", cont: str = "") -> dict:
        """Одна страница истории операций. cont — значение «continue» из прошлой страницы."""
        self._need_login()
        r = self._xhr("users/transactions", {"user_id": self.account.id, "continue": cont or "", "filter": filter_ or ""})
        bs = BeautifulSoup(r.text, "html.parser")
        items = []
        for it in bs.select(".tc-item"):
            cls = " ".join(it.get("class", []))
            m = re.search(r"transaction-status-(\w+)", cls)
            price = _text(it.select_one(".tc-price"))
            title = _text(it.select_one(".tc-title"))
            order = re.search(r"Заказ #(\w+)", title)
            items.append({
                "id": it.get("data-transaction"),
                "date": _text(it.select_one(".tc-date-time")),
                "ago": _text(it.select_one(".tc-date-left")),
                "title": title,
                "status": _text(it.select_one(".tc-status")),
                "state": m.group(1) if m else "",
                "amount": price,
                "sign": "+" if price.startswith("+") else ("-" if price[:1] in "-−" else ""),
                "order": order.group(1) if order else "",
            })
        nxt = bs.select_one("[name=continue]")
        return {"items": items, "next": nxt.get("value", "") if nxt else ""}

    def _withdraw_data(self, currency: str, method: str, wallet: str, amount: str, bank: str = "") -> dict:
        if not getattr(self, "_wd_csrf", None):
            self.finance()
        data = {"csrf_token": self._wd_csrf, "currency_id": currency, "ext_currency_id": method,
                "wallet": (wallet or "").strip(), "amount_int": str(amount or "").replace(",", ".").strip()}
        if method == "fps":
            data["wallet_extra"] = bank or ""
        return data

    def withdraw_calc(self, currency: str, method: str, amount: str, wallet: str = "", bank: str = "") -> dict:
        """Сколько придёт после комиссии (ничего не выводит)."""
        data = self._withdraw_data(currency, method, wallet, amount, bank)
        data["preview"] = "1"
        try:
            return self._xhr("withdraw/calc", data).json()
        except ValueError:
            raise FunPayError("FunPay не смог посчитать сумму к получению.")

    def withdraw(self, currency: str, method: str, wallet: str, amount: str, bank: str = "",
                 confirm: bool = False, twofactor: str = "") -> dict:
        """Вывод в два шага, как на сайте.
        confirm=False — предпросмотр: FunPay проверяет данные и возвращает итог, деньги НЕ списываются.
        confirm=True — настоящая заявка на вывод (с кодом 2FA, если он включён)."""
        data = self._withdraw_data(currency, method, wallet, amount, bank)
        data["preview"] = "" if confirm else "1"
        if confirm and twofactor:
            data["twofactor_code"] = re.sub(r"\s", "", twofactor)
        r = self._xhr("withdraw/withdraw", data)
        try:
            js = r.json()
        except ValueError:
            raise FunPayError(f"Неожиданный ответ FunPay: {r.text[:200]}")
        if js.get("twofactor_error"):
            raise FunPayError(js.get("twofactor_msg") or "Неверный код 2FA")
        if js.get("error"):
            raise FunPayError(js.get("msg") or "FunPay отклонил вывод")
        if confirm:
            self._wd_csrf = None  # после вывода страница выдаёт новый токен
            return {"done": True, "url": js.get("url", "")}
        return {"wallet": js.get("wallet", data["wallet"]), "amount_int": js.get("amount_int"),
                "amount_ext": js.get("amount_ext"), "bank": js.get("fps_bank_name") or "",
                "twofactor": bool(js.get("twofactor_enabled"))}

    def delete(self, node: int, offer: int) -> dict:
        return self._modify(node, offer, {"deleted": "1"})

    def set_active(self, node: int, offer: int, active: bool) -> dict:
        return self._modify(node, offer, {"active": bool(active)})

    def bulk_edit(self, node: int, offer: int, replace: list | None = None, price: dict | None = None) -> dict:
        """Массовая правка одного лота: замены текста в описаниях и/или изменение цены.
        replace: [{"find": str, "to": str}], price: {"mode": "set"|"percent"|"add", "value": float}.
        Возвращает {"changed": bool, "price": новая цена}."""
        form = self.get_form(node, offer)
        changed = False
        text_fields = {f"fields[{k}][{l}]" for k in ("summary", "desc", "payment_msg") for l in ("ru", "en")}
        for f in form["fields"]:
            if replace and f["name"] in text_fields and f.get("value"):
                v = f["value"]
                for r in replace:
                    if r.get("find"):
                        v = v.replace(r["find"], r.get("to", ""))
                if v != f["value"]:
                    f["value"], changed = v, True
            if price and f["name"] == "price":
                try:
                    cur = float(str(f["value"]).replace(",", ".") or 0)
                    val = float(price["value"])
                except (TypeError, ValueError):
                    raise FunPayError("Неверное значение цены.")
                new = {"set": val, "percent": cur * (1 + val / 100), "add": cur + val}.get(price.get("mode"), cur)
                new = round(max(new, 0), 2)
                if new <= 0:
                    raise FunPayError(f"Цена лота #{offer} получилась бы нулевой или отрицательной — лот пропущен.")
                if new != cur:
                    f["value"], changed = (f"{new:.2f}".rstrip("0").rstrip(".")), True
        if changed:
            self.save(form["fields"])
        p = next((f["value"] for f in form["fields"] if f["name"] == "price"), "")
        return {"changed": changed, "price": p}

    # ---------- поднятие ----------
    def raise_lots(self, node: int, all_nodes: list[int] | None = None) -> dict:
        """Поднимает лоты игры, к которой относится раздел node (вместе с остальными вашими разделами этой игры).
        Возвращает {"ok": True, "msg"} или {"ok": False, "msg", "wait": секунды до следующей попытки}."""
        self._need_login()
        game = self.node_games.get(node)
        if game is None:
            self.category_lots(node)
            game = self.node_games.get(node)
        if game is None:
            raise FunPayError(f"В разделе {node} нет кнопки поднятия.")
        nodes = sorted({node, *[n for n in (all_nodes or []) if self.node_games.get(n) == game]})
        data = [("game_id", str(game)), ("node_id", str(node))] + [("node_ids[]", str(n)) for n in nodes]
        try:
            r = self.s.post(f"{BASE}/lots/raise", data=data, timeout=TIMEOUT,
                            headers={"accept": "*/*", "x-requested-with": "XMLHttpRequest", "origin": BASE,
                                     "referer": f"{BASE}/lots/{node}/trade"})
            js = r.json()
        except (requests.RequestException, ValueError) as e:
            raise FunPayError(f"Не удалось поднять лоты: {e}") from e
        msg = re.sub(r"<[^>]+>", " ", str(js.get("msg") or "")).strip()
        if js.get("modal"):
            # FunPay спросил, какие разделы поднять, — отвечаем всеми нашими разделами этой игры.
            mb = BeautifulSoup(js["modal"], "html.parser")
            ids = [i.get("value") for i in mb.select("input[name='node_ids[]']") if i.get("value")]
            if ids:
                data = [("game_id", str(game)), ("node_id", str(node))] + [("node_ids[]", i) for i in ids]
                js = self.s.post(f"{BASE}/lots/raise", data=data, timeout=TIMEOUT,
                                 headers={"accept": "*/*", "x-requested-with": "XMLHttpRequest"}).json()
                msg = re.sub(r"<[^>]+>", " ", str(js.get("msg") or "")).strip()
        if js.get("error"):
            return {"ok": False, "msg": msg or "FunPay не поднял лоты", "wait": parse_wait(msg), "game": game}
        return {"ok": True, "msg": msg or "Предложения подняты", "wait": 0, "game": game}

    # ---------- заказы ----------
    def orders(self, cont: str = "", state: str = "") -> dict:
        """Страница продаж (до 100 заказов). state: "" | "paid" | "closed" | "refunded"."""
        self._need_login()
        q = f"orders/trade?state={state}" if state else "orders/trade"
        if cont:
            try:
                r = self.s.post(f"{BASE}/{q}", data={"continue": cont, **({"state": state} if state else {})},
                                timeout=TIMEOUT, headers={"x-requested-with": "XMLHttpRequest"})
            except requests.RequestException as e:
                raise FunPayError(f"Нет связи с FunPay: {e}") from e
            html = r.text
        else:
            html = self._get(q).text
        bs = BeautifulSoup(html, "html.parser")
        items = []
        for a in bs.select("a.tc-item"):
            cls = a.get("class", [])
            status = "refunded" if "warning" in cls else "paid" if "info" in cls else "closed"
            price_el = a.select_one(".tc-price")
            unit = _text(price_el.select_one(".unit")) if price_el else ""
            buyer = a.select_one(".media-user-name [data-href]")
            bid = re.search(r"/users/(\d+)/", buyer.get("data-href", "")) if buyer else None
            date_text = _text(a.select_one(".tc-date-time"))
            desc = a.select_one(".order-desc")
            items.append({
                "id": _text(a.select_one(".tc-order")).lstrip("#"),
                "date": date_text,
                "ts": parse_date(date_text),
                "title": _text(desc.find("div")) if desc else "",
                "category": _text(a.select_one(".order-desc .text-muted")),
                "buyer": _text(buyer),
                "buyer_id": int(bid.group(1)) if bid else 0,
                "status": status,
                "status_text": _text(a.select_one(".tc-status")),
                "amount": _text(price_el).replace(unit, "").strip() if price_el else "",
                "unit": unit,
            })
        nxt = bs.select_one("input[name=continue]")
        return {"items": items, "next": nxt.get("value", "") if nxt and items else ""}

    def order(self, order_id: str) -> dict:
        self._need_login()
        bs = BeautifulSoup(self._get(f"orders/{order_id}/").text, "html.parser")
        params = []
        for d in bs.select(".param-item"):
            h = d.find("h5")
            if not h:
                continue
            name = _text(h)
            if name == "Действия":
                continue
            body = d.find("div")
            val = body.get_text("\n", strip=True) if body else _text(d).replace(name, "", 1).strip()
            params.append({"name": name, "value": val})
        rv = bs.select_one(".order-review")
        rating = None
        if rv:
            stars = rv.select_one(".rating div[class*=rating]")
            m = re.search(r"rating(\d)", " ".join(stars.get("class", []))) if stars else None
            rating = int(m.group(1)) if m else None
        review_text = _text(rv.select_one(".review-compiled-review .review-item-text")) if rv else ""
        if "Отсутствует" in review_text:
            review_text = ""
        reply_el = rv.select_one(".review-compiled-reply > div:not(.review-controls)") if rv else None
        reply = _text(reply_el)
        chat = bs.select_one(".chat[data-id]")
        status = _text(bs.select_one(".page-header .text-success, .page-header .text-warning, .page-header span[class*=text-]"))
        return {
            "id": order_id, "params": params, "status": status,
            "review": {"rating": rating, "text": review_text, "reply": reply,
                       "can_reply": bool(review_text)},
            "chat_id": int(chat["data-id"]) if chat else None,
            "buyer": _text(bs.select_one(".chat-header .media-user-name a")),
            "can_refund": bool(bs.select_one("button.btn-refund")),
        }

    def refund(self, order_id: str) -> dict:
        self._need_login()
        js = self._xhr("orders/refund", {"id": order_id, "csrf_token": self.account.csrf}).json()
        if js.get("error"):
            raise FunPayError(js.get("msg") or "FunPay не оформил возврат.")
        return {"done": True}

    def review_reply(self, order_id: str, text: str) -> dict:
        self._need_login()
        if not (text or "").strip():
            raise FunPayError("Ответ на отзыв пустой.")
        try:
            r = self.s.post(f"{BASE}/orders/review", timeout=TIMEOUT,
                            data={"authorId": self.account.id, "text": text.strip(), "rating": 5,
                                  "csrf_token": self.account.csrf, "orderId": order_id},
                            headers={"accept": "*/*", "x-requested-with": "XMLHttpRequest"})
            js = r.json()
        except (requests.RequestException, ValueError) as e:
            raise FunPayError(f"Не удалось отправить ответ: {e}") from e
        if r.status_code != 200 or js.get("error"):
            raise FunPayError(js.get("msg") or f"FunPay не принял ответ ({r.status_code}).")
        return {"done": True}

    # ---------- чаты ----------
    def _runner(self, objects: list, request=False) -> dict:
        self._need_login()
        payload = {"objects": json.dumps(objects), "request": json.dumps(request) if request else "false",
                   "csrf_token": self.account.csrf}
        r = self._xhr("runner/", payload)
        try:
            return r.json()
        except ValueError:
            raise FunPayError("FunPay вернул неожиданный ответ чата.")

    def chats(self) -> list[dict]:
        js = self._runner([{"type": "chat_bookmarks", "id": self.account.id, "tag": "00000000", "data": False}])
        html = next((o["data"]["html"] for o in js.get("objects", []) if o.get("type") == "chat_bookmarks"), "")
        out = []
        for a in BeautifulSoup(html, "html.parser").select("a.contact-item"):
            out.append({
                "id": int(a["data-id"]),
                "name": _text(a.select_one(".media-user-name")),
                "last": _text(a.select_one(".contact-item-message")),
                "time": _text(a.select_one(".contact-item-time")),
                "unread": "unread" in a.get("class", []),
                "msg_id": int(a.get("data-node-msg") or 0),
            })
        return out

    def chat_history(self, chat_id: int) -> dict:
        self._need_login()
        r = self._get(f"chat/history?node={int(chat_id)}&last_message=999999999999",
                      headers={"x-requested-with": "XMLHttpRequest", "accept": "*/*"})
        try:
            js = r.json()
        except ValueError:
            raise FunPayError("Не удалось загрузить чат.")
        chat = js.get("chat") or {}
        msgs = []
        for m in chat.get("messages") or []:
            bs = BeautifulSoup(m.get("html", ""), "html.parser")
            text_el = bs.select_one(".chat-msg-text, .message-text")
            alert = bs.select_one(".alert")
            img = bs.select_one("a.chat-img-link")
            text = text_el.get_text("\n", strip=True) if text_el else (alert.get_text(" ", strip=True) if alert else "")
            author = int(m.get("author") or 0)
            msgs.append({
                "id": m.get("id"), "author": author,
                "mine": author == self.account.id, "system": author == 0,
                "name": _text(bs.select_one(".media-user-name a, .chat-msg-author-link")) or None,
                "time": _text(bs.select_one(".chat-msg-date, .message-time")),
                "text": text, "image": img.get("href") if img else None,
            })
        name = (chat.get("node") or {}).get("name", "")
        return {"id": int(chat_id), "messages": msgs, "node_name": name}

    def send_message(self, chat_id: int, text: str) -> dict:
        if not (text or "").strip():
            raise FunPayError("Пустое сообщение.")
        cid = int(chat_id)
        objects = [{"type": "chat_node", "id": cid, "tag": "00000000",
                    "data": {"node": cid, "last_message": -1, "content": ""}}]
        request = {"action": "chat_message", "data": {"node": cid, "last_message": -1, "content": text.strip()}}
        js = self._runner(objects, request)
        resp = js.get("response")
        if not resp:
            raise FunPayError("Сообщение не доставлено.")
        if resp.get("error"):
            raise FunPayError(f"Сообщение не доставлено: {resp['error']}")
        return {"done": True}

    # ---------- конкуренты ----------
    def public_offers(self, node: int, mine_ids: set | None = None) -> dict:
        """Все предложения раздела на витрине FunPay (как их видят покупатели, цены с комиссией).
        Свои лоты на витрине идут без data-user, поэтому отмечаются по ID из mine_ids."""
        mine_ids = mine_ids or set()
        self._need_login()
        bs = BeautifulSoup(self._get(f"lots/{int(node)}/").text, "html.parser")
        offers = []
        for a in bs.select("a.tc-item"):
            m = re.search(r"id=(\d+)", a.get("href", ""))
            price_el = a.select_one(".tc-price")
            try:
                price = float(price_el.get("data-s")) if price_el else None
            except (TypeError, ValueError):
                price = None
            if not m or price is None:
                continue
            title = _text(a.select_one(".tc-desc-text"))
            offers.append({
                "id": int(m.group(1)),
                "mine": int(m.group(1)) in mine_ids,
                "user_id": int(a.get("data-user") or 0),
                "seller": _text(a.select_one(".media-user-name")),
                "online": a.get("data-online") == "1",
                "auto": a.get("data-auto") == "1",
                "promo": "offer-promo" in a.get("class", []),
                "filters": {k[7:]: v for k, v in a.attrs.items() if k.startswith("data-f-")},
                "title": title,
                "minutes": parse_duration(title),
                "price": round(price, 2),
                "unit": _text(price_el.select_one(".unit")) if price_el else "",
                "reviews": _text(a.select_one(".rating-mini-count")),
            })
        return {"node": int(node), "offers": offers, "me": self.account.id}


MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7,
          "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12}


def parse_date(text: str) -> int:
    """«сегодня, 11:52» / «вчера, 22:11» / «2 ноября, 10:03» / «12 октября 2025, 10:03» → unix-время (локальное)."""
    import datetime as dt
    t = (text or "").strip().lower()
    now = dt.datetime.now()
    m = re.search(r"(\d{1,2}):(\d{2})", t)
    if not m:
        return 0
    h, mi = int(m.group(1)), int(m.group(2))
    try:
        if t.startswith("сегодня"):
            d = now.date()
        elif t.startswith("вчера"):
            d = (now - dt.timedelta(days=1)).date()
        else:
            dm = re.match(r"(\d{1,2})\s+([а-я]+)(?:\s+(\d{4}))?", t)
            if not dm or dm.group(2) not in MONTHS:
                return 0
            year = int(dm.group(3)) if dm.group(3) else now.year
            d = dt.date(year, MONTHS[dm.group(2)], int(dm.group(1)))
            if not dm.group(3) and d > now.date():  # «31 декабря» в январе — это прошлый год
                d = d.replace(year=year - 1)
        return int(dt.datetime(d.year, d.month, d.day, h, mi).timestamp())
    except ValueError:
        return 0


def parse_duration(title: str) -> int | None:
    """Срок аренды из названия: «НА 3 ЧАСА», «на 30 минут», «1 МЕСЯЦ», «24 ч» → минуты. None, если не найдено."""
    t = (title or "").lower()
    units = [(r"мес", 30 * 24 * 60), (r"(?:нед|week)", 7 * 24 * 60), (r"(?:дн|день|сут|day)", 24 * 60),
             (r"(?:час|ч\b|hour|h\b)", 60), (r"(?:мин|min)", 1)]
    for pat, mult in units:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*" + pat, t)
        if m:
            return int(float(m.group(1).replace(",", ".")) * mult)
    return None


def parse_wait(msg: str) -> int:
    """«Подождите 2 часа.» / «Подождите 35 минут.» / «Подождите 1 час 20 минут» → секунды (0, если не распознано)."""
    t = (msg or "").lower()
    total = 0
    for num, unit in re.findall(r"(\d+)\s*(час|мин|сек)", t):
        total += int(num) * {"час": 3600, "мин": 60, "сек": 1}[unit]
    if not total and "подожд" in t:
        total = 3600 if "час" in t else 60 if "минут" in t else 0
    return total
