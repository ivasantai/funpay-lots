"""Фоновая работа: автоподнятие, уведомления о заказах и сообщениях, таймер аренды, значок в трее."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import threading
import time
import traceback

from funpay_client import FunPayClient, FunPayError

log = logging.getLogger("funpay-lots.bg")


# ---------- уведомления ОС ----------

class Notifier:
    def __init__(self):
        self.tray = None  # pystray.Icon на Windows

    def os_notify(self, title: str, text: str):
        try:
            if sys.platform == "win32" and self.tray is not None:
                self.tray.notify(text[:250], title[:60])
            elif sys.platform == "darwin":
                script = f'display notification {json.dumps(text[:250])} with title {json.dumps(title[:60])}'
                subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith("linux") and shutil.which("notify-send"):
                subprocess.Popen(["notify-send", "-a", "FunPay Lots", title[:60], text[:250]],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:  # уведомление не должно ронять приложение
            log.warning("notify failed: %s", traceback.format_exc())


# ---------- значок в трее (Windows) ----------

def start_tray(api, icon_path: str) -> bool:
    """Значок в области уведомлений Windows: «Открыть», «Поднять лоты сейчас», «Выход».
    На macOS и Linux окно при закрытии сворачивается в Dock/панель задач (см. Api.on_closing)."""
    if sys.platform != "win32":
        return False
    try:
        import pystray
        from PIL import Image
    except Exception:
        return False

    def show(icon=None, item=None):
        api.show_window()

    def raise_now(icon=None, item=None):
        threading.Thread(target=api.bg_raise_now, daemon=True).start()

    def quit_app(icon=None, item=None):
        api.quit_app()

    menu = pystray.Menu(
        pystray.MenuItem("Открыть FunPay Lots", show, default=True),
        pystray.MenuItem("Поднять лоты сейчас", raise_now),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход", quit_app),
    )
    icon = pystray.Icon("FunPayLots", Image.open(icon_path), "FunPay Lots", menu)
    icon.run_detached()
    api._notifier.tray = icon
    return True


# ---------- фоновый цикл ----------

class Worker(threading.Thread):
    """Раз в несколько секунд проверяет, что пора сделать: поднять лоты, сообщить о заказе/сообщении,
    закончилась ли аренда. Все сетевые ошибки глотаются и пишутся в журнал — фон не должен падать."""

    TICK = 10

    def __init__(self, api):
        super().__init__(daemon=True, name="funpay-bg")
        self.api = api
        self.stop_event = threading.Event()
        self.last_orders_check = 0.0
        self.last_chats_check = 0.0
        self.seen_orders: dict[str, set] = {}
        self.seen_msgs: dict[str, dict] = {}
        self.wake = threading.Event()

    def run(self):
        while not self.stop_event.is_set():
            try:
                self.step()
            except Exception:
                log.warning("bg step failed: %s", traceback.format_exc())
            self.wake.wait(self.TICK)
            self.wake.clear()

    def step(self):
        api = self.api
        now = time.time()
        for uid, acc in list(api._store.data.get("accounts", {}).items()):
            ar = acc.get("autoraise") or {}
            if ar.get("enabled"):
                self.autoraise(uid, acc, now)
        uid = api._active_uid()
        if not uid or not api._fp:
            return
        s = api._store.data
        if now - self.last_orders_check > 60 and (s.get("notify_orders", True) or s.get("rental_notify", True)
                                                 or s.get("rental_auto_msg")):
            self.last_orders_check = now
            self.check_orders(uid)
        if now - self.last_chats_check > 30 and s.get("notify_chats", True):
            self.last_chats_check = now
            self.check_chats(uid)

    # --- автоподнятие ---
    def autoraise(self, uid: str, acc: dict, now: float):
        ar = acc.setdefault("autoraise", {})
        nxt = ar.setdefault("next", {})
        last = ar.setdefault("last", {})
        client = self.api._client_for(uid)
        if client is None:
            return
        nodes = [int(n) for n in (ar.get("nodes") or acc.get("nodes", {}).keys())]
        if not nodes:
            return
        changed = False
        for n in nodes:
            if n not in client.node_games:
                try:
                    client.category_lots(n)
                except FunPayError:
                    continue
        games: dict[int, int] = {}
        for n in nodes:
            g = client.node_games.get(n)
            if g is not None and g not in games:
                games[g] = n
        for game, node in games.items():
            if nxt.get(str(game), 0) > now:
                continue
            try:
                res = client.raise_lots(node, nodes)
            except FunPayError as e:
                res = {"ok": False, "msg": str(e), "wait": 600}
            wait = res.get("wait") or (4 * 3600 if res["ok"] else 600)
            # FunPay округляет «Подождите час» — пробуем чуть позже названного срока.
            nxt[str(game)] = now + wait + 90
            last[str(game)] = {"ts": now, "ok": res["ok"], "msg": res["msg"], "node": node,
                               "name": acc.get("nodes", {}).get(str(node), f"Раздел {node}")}
            changed = True
            if res["ok"] and self.api._store.data.get("notify_raise", False):
                self.api.notify("Лоты подняты", last[str(game)]["name"])
        if changed:
            self.api._store.save()
            self.api.push_event("autoraise", {"uid": uid})

    # --- заказы и аренды ---
    def check_orders(self, uid: str):
        api = self.api
        s = api._store.data
        page = api._fp.orders()
        items = page["items"]
        seen = self.seen_orders.get(uid)
        ids = {o["id"] for o in items}
        if seen is None:
            self.seen_orders[uid] = ids  # первый проход — только запоминаем
        else:
            new = [o for o in items if o["id"] not in seen and o["status"] == "paid"]
            self.seen_orders[uid] = seen | ids
            if new and s.get("notify_orders", True):
                for o in new[:3]:
                    api.notify(f"Новый заказ #{o['id']}", f"{o['buyer']}: {o['amount']} {o['unit']} — {o['title'][:80]}")
                api.push_event("orders", {"new": len(new)})
        import features
        acc = api._acc()
        done = acc.setdefault("rentals_done", [])
        warned = acc.setdefault("rentals_warned", [])
        now = time.time()
        for r in features.rentals(items, now, int(s.get("rental_bonus", 0)), acc.get("rentals_extra")):
            if r["active"] and 0 < r["left"] <= 600 and r["id"] not in warned and s.get("rental_notify", True):
                warned.append(r["id"])
                api.notify("Аренда скоро закончится", f"#{r['id']} {r['buyer']}: осталось {max(1, r['left'] // 60)} мин")
            if not r["active"] and r["id"] not in done and now - r["end"] < 1800:
                done.append(r["id"])
                if s.get("rental_notify", True):
                    api.notify("Аренда закончилась", f"#{r['id']} {r['buyer']} — {r['title'][:60]}")
                if s.get("rental_auto_msg") and (s.get("rental_msg") or "").strip():
                    try:
                        info = api._fp.order(r["id"])
                        if info.get("chat_id"):
                            text = s["rental_msg"].replace("{buyer}", r["buyer"]).replace("{order}", r["id"])
                            api._fp.send_message(info["chat_id"], text)
                    except FunPayError as e:
                        log.warning("rental message failed: %s", e)
        del done[:-500], warned[:-500]
        api._store.save()
        api.push_event("rentals", {})

    # --- сообщения ---
    def check_chats(self, uid: str):
        api = self.api
        chats = api._fp.chats()
        last = self.seen_msgs.get(uid)
        cur = {c["id"]: c["msg_id"] for c in chats}
        self.seen_msgs[uid] = cur
        if last is None:
            return
        fresh = [c for c in chats if c["unread"] and c["msg_id"] > last.get(c["id"], 0)]
        for c in fresh[:3]:
            api.notify(f"Сообщение от {c['name']}", c["last"][:200])
        if fresh:
            api.push_event("chats", {"new": len(fresh)})
