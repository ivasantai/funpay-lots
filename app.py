"""FunPay Lots — десктоп-приложение для управления лотами FunPay."""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import webview

import updater
from funpay_client import FunPayClient, FunPayError

APP_NAME = "FunPay Lots"
VERSION = "1.6.2"
# Для проверки автообновления: FPL_VERSION_OVERRIDE=1.0.0 заставит приложение считать себя старой версией.
RUNTIME_VERSION = os.environ.get("FPL_VERSION_OVERRIDE") or VERSION


def resource(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def page_html() -> str:
    """Интерфейс отдаётся в окно строкой, а не через встроенный HTTP-сервер pywebview:
    сервер при запуске резолвит имя компьютера, и macOS 15 из-за этого спрашивает доступ к локальной сети.
    Иконка встраивается в страницу как data URI."""
    import base64
    html = resource("ui/index.html").read_text(encoding="utf-8")
    icon = "data:image/png;base64," + base64.b64encode(resource("ui/icon.png").read_bytes()).decode()
    return html.replace('src="icon.png"', f'src="{icon}"').replace('href="icon.png"', f'href="{icon}"')


def config_dir() -> Path:
    if sys.platform == "darwin":
        d = Path.home() / "Library" / "Application Support" / "FunPayLots"
    elif os.name == "nt":
        d = Path(os.environ.get("APPDATA", Path.home())) / "FunPayLots"
    else:
        d = Path.home() / ".config" / "funpay-lots"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Store:
    def __init__(self):
        self.path = config_dir() / "config.json"
        self.lock = threading.Lock()
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}
        # Аккаунты: {id: {golden_key, username, nodes, autoraise, ...}}; "active" — текущий.
        # До 1.6.0 ключ и разделы лежали в корне — переносим их при первом входе (см. Api.login).
        self.data.setdefault("accounts", {})
        self.data.setdefault("templates", [])

    def save(self):
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
            if os.name != "nt":
                os.chmod(self.path, 0o600)


def api_call(fn):
    """Оборачивает метод API: ответ всегда {ok, data} или {ok:false, error}."""
    def wrapper(self, *a, **kw):
        try:
            return {"ok": True, "data": fn(self, *a, **kw)}
        except (FunPayError, updater.UpdateError) as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            if type(e).__name__ in ("AIError", "FreeTranslateError"):  # модули грузятся лениво
                return {"ok": False, "error": str(e)}
            traceback.print_exc()
            return {"ok": False, "error": f"Внутренняя ошибка: {e}"}
    wrapper.__name__ = fn.__name__
    return wrapper


SETTINGS_KEYS = {  # простые настройки, которые интерфейс может менять напрямую (ключ -> значение по умолчанию)
    "theme": "auto", "close_to_background": False, "notify_orders": True, "notify_chats": True,
    "notify_raise": False, "auto_update_check": True, "rental_notify": True, "rental_auto_msg": False, "rental_bonus": 0,
    "rental_msg": "Здравствуйте, {buyer}! Время аренды по заказу #{order} закончилось. Спасибо за покупку — "
                  "будем рады отзыву 🙌",
}


class Api:
    def __init__(self):
        self._store = Store()
        self._fp: FunPayClient | None = None
        self._clients: dict[str, FunPayClient] = {}
        self._window = None
        self._update: dict | None = None
        self._progress = 0.0
        self._quitting = False
        self._events: list[dict] = []
        self._ev_lock = threading.Lock()
        import background
        self._notifier = background.Notifier()
        self._worker = background.Worker(self)

    # ---------- служебное ----------
    def _client(self) -> FunPayClient:
        if not self._fp:
            raise FunPayError("Сначала войдите по ключу.")
        return self._fp

    def _active_uid(self) -> str | None:
        return self._store.data.get("active")

    def _acc(self) -> dict:
        uid = self._active_uid()
        if not uid:
            raise FunPayError("Сначала войдите по ключу.")
        return self._store.data["accounts"].setdefault(uid, {})

    def _client_for(self, uid: str) -> FunPayClient | None:
        """Клиент для фоновых задач любого сохранённого аккаунта (у активного — тот же, что у окна)."""
        if uid == self._active_uid() and self._fp:
            return self._fp
        c = self._clients.get(uid)
        if c is None:
            key = (self._store.data["accounts"].get(uid) or {}).get("golden_key")
            if not key:
                return None
            try:
                c = FunPayClient(key)
                c.login()
            except FunPayError:
                return None
            self._clients[uid] = c
        return c

    def notify(self, title: str, text: str):
        """Уведомление: всплывашка в окне + системное уведомление ОС."""
        self.push_event("notify", {"title": title, "text": text})
        self._notifier.os_notify(title, text)

    def push_event(self, kind: str, data: dict):
        with self._ev_lock:
            self._events.append({"kind": kind, **data})
            del self._events[:-50]

    @api_call
    def events(self):
        """Интерфейс забирает накопившиеся события фоновых задач (раз в несколько секунд)."""
        with self._ev_lock:
            ev, self._events = self._events, []
        return ev

    # ---------- окно и фон ----------
    def show_window(self):
        if self._window:
            self._window.show()
            try:
                self._window.restore()
            except Exception:
                pass

    def quit_app(self):
        self._quitting = True
        self._worker.stop_event.set()
        if self._notifier.tray is not None:
            try:
                self._notifier.tray.stop()
            except Exception:
                pass
        if self._window:
            self._window.destroy()

    def on_closing(self):
        """Закрытие окна: если включён фон — прячем окно вместо выхода (False отменяет закрытие)."""
        if self._quitting or not self._store.data.get("close_to_background"):
            self._quitting = True
            if self._notifier.tray is not None:
                try:
                    self._notifier.tray.stop()
                except Exception:
                    pass
            return True
        if self._notifier.tray is not None:  # Windows: прячем в трей
            self._window.hide()
            self._notifier.os_notify("FunPay Lots работает в фоне", "Значок — в области уведомлений. Выход — через его меню.")
        else:  # macOS/Linux: сворачиваем в Dock/панель задач
            self._window.minimize()
        return False

    def bg_raise_now(self):
        for acc in self._store.data["accounts"].values():
            (acc.get("autoraise") or {}).get("next", {}).clear()
        self._worker.wake.set()

    # ---------- состояние и настройки ----------
    @api_call
    def state(self):
        s = self._store.data
        has_key = bool(s.get("golden_key")) or any(a.get("golden_key") for a in s["accounts"].values())
        return {"has_key": has_key, "version": RUNTIME_VERSION, "skipped": s.get("skip_version", ""),
                "settings": {k: s.get(k, v) for k, v in SETTINGS_KEYS.items()},
                "tray": self._notifier.tray is not None, "platform": sys.platform}

    @api_call
    def set_setting(self, key: str, value):
        if key not in SETTINGS_KEYS:
            raise FunPayError("Неизвестная настройка.")
        default = SETTINGS_KEYS[key]
        if isinstance(default, bool):
            value = bool(value)
        elif isinstance(default, int):
            value = max(0, min(int(value or 0), 600))
        else:
            value = str(value)[:2000]
        self._store.data[key] = value
        self._store.save()
        return value

    # ---------- аккаунты ----------
    @api_call
    def login(self, key: str | None = None, remember: bool = True):
        s = self._store.data
        if not key:
            uid = s.get("active")
            key = (s["accounts"].get(uid) or {}).get("golden_key") if uid else None
            key = key or s.get("golden_key") or next((a["golden_key"] for a in s["accounts"].values()
                                                      if a.get("golden_key")), None)
        if not key:
            raise FunPayError("Введите golden_key.")
        client = FunPayClient(key)
        acc = client.login()
        uid = str(acc.id)
        entry = s["accounts"].setdefault(uid, {})
        entry["username"] = acc.username
        if remember:
            entry["golden_key"] = key.strip()
        else:
            entry.pop("golden_key", None)
        # Перенос настроек версии до 1.6.0 (один аккаунт в корне файла).
        if "nodes" in s and not entry.get("nodes"):
            entry["nodes"] = s.pop("nodes")
        s.pop("golden_key", None)
        entry.setdefault("nodes", {})
        s["active"] = uid
        self._fp = client
        self._clients[uid] = client
        self._store.save()
        return {"id": acc.id, "username": acc.username, "balance": acc.balance}

    @api_call
    def accounts(self):
        s = self._store.data
        return [{"id": uid, "username": a.get("username", uid), "active": uid == s.get("active"),
                 "saved": bool(a.get("golden_key")),
                 "autoraise": bool((a.get("autoraise") or {}).get("enabled"))}
                for uid, a in s["accounts"].items()]

    @api_call
    def switch_account(self, uid: str):
        a = self._store.data["accounts"].get(str(uid))
        if not a or not a.get("golden_key"):
            raise FunPayError("Для этого аккаунта не сохранён ключ — войдите заново.")
        r = self.login(a["golden_key"], True)
        if not r["ok"]:
            raise FunPayError(r["error"])
        return r["data"]

    @api_call
    def logout(self):
        """Выход из текущего аккаунта: ключ удаляется; если есть другие сохранённые — остаёмся без входа."""
        s = self._store.data
        uid = s.get("active")
        if uid:
            s["accounts"].pop(uid, None)
            self._clients.pop(uid, None)
        s["active"] = next(iter(s["accounts"]), None)
        self._fp = None
        self._store.save()
        return {"others": len(s["accounts"])}

    @api_call
    def lots(self):
        c = self._client()
        acc = self._acc()
        acc.setdefault("nodes", {})
        nodes: dict[int, str] = {int(k): v for k, v in acc["nodes"].items()}
        for n, name in c.profile_categories().items():
            nodes[n] = name or nodes.get(n, "")

        def load(n):
            try:
                name, lots = c.category_lots(n)
                return n, name, lots, None
            except FunPayError as e:
                return n, "", [], str(e)

        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(load, nodes))
        cats = []
        for n, page_name, lots, err in results:
            name = nodes.get(n) or page_name or f"Раздел {n}"
            if not err:
                acc["nodes"][str(n)] = name
            cats.append({"node": n, "name": name, "lots": lots, "error": err, "game": c.node_games.get(n)})
        self._store.save()
        cats.sort(key=lambda x: x["name"].lower())
        return cats

    @api_call
    def games(self):
        return self._client().games()

    @api_call
    def form(self, node: int, offer: int | None = None):
        return self._client().get_form(int(node), int(offer) if offer else None)

    @api_call
    def save(self, node: int, fields: list, category_name: str = ""):
        res = self._client().save(fields)
        key = str(int(node))
        nodes = self._acc().setdefault("nodes", {})
        if category_name or key not in nodes:
            nodes[key] = category_name or nodes.get(key) or f"Раздел {node}"
            self._store.save()
        return res

    @api_call
    def delete(self, node: int, offer: int):
        return self._client().delete(int(node), int(offer))

    @api_call
    def set_active(self, node: int, offer: int, active: bool):
        return self._client().set_active(int(node), int(offer), bool(active))

    @api_call
    def forget_category(self, node: int):
        self._acc().setdefault("nodes", {}).pop(str(int(node)), None)
        self._store.save()
        return True

    # ---------- массовые правки ----------
    @api_call
    def bulk_edit(self, node: int, offer: int, replace: list | None = None, price: dict | None = None):
        return self._client().bulk_edit(int(node), int(offer), replace or [], price or None)

    # ---------- автоподнятие ----------
    @api_call
    def autoraise_state(self):
        acc = self._acc()
        ar = acc.setdefault("autoraise", {})
        return {"enabled": bool(ar.get("enabled")), "nodes": ar.get("nodes") or [],
                "next": ar.get("next", {}), "last": ar.get("last", {}),
                "background": bool(self._store.data.get("close_to_background"))}

    @api_call
    def autoraise_set(self, enabled: bool, nodes: list | None = None):
        ar = self._acc().setdefault("autoraise", {})
        ar["enabled"] = bool(enabled)
        ar["nodes"] = [int(n) for n in (nodes or [])]
        if enabled:
            ar.setdefault("next", {}).clear()  # первая попытка — сразу
        self._store.save()
        self._worker.wake.set()
        return True

    @api_call
    def raise_now(self, node: int):
        c = self._client()
        acc = self._acc()
        res = c.raise_lots(int(node), [int(n) for n in acc.get("nodes", {})])
        ar = acc.setdefault("autoraise", {})
        g = str(res["game"])
        ar.setdefault("last", {})[g] = {"ts": time.time(), "ok": res["ok"], "msg": res["msg"], "node": int(node),
                                        "name": acc.get("nodes", {}).get(str(node), f"Раздел {node}")}
        ar.setdefault("next", {})[g] = time.time() + (res["wait"] or 4 * 3600) + 90
        self._store.save()
        return res

    # ---------- шаблоны ----------
    @api_call
    def templates(self):
        return self._store.data["templates"]

    @api_call
    def template_save(self, name: str, fields: dict):
        name = (name or "").strip()[:80]
        if not name:
            raise FunPayError("Назовите шаблон.")
        clean = {k: str(v) for k, v in (fields or {}).items() if k.startswith("fields[") and v}
        if not clean:
            raise FunPayError("В шаблоне нет текста.")
        tpls = self._store.data["templates"]
        tpls[:] = [t for t in tpls if t["name"] != name]
        tpls.append({"id": str(int(time.time() * 1000)), "name": name, "fields": clean})
        self._store.save()
        return tpls

    @api_call
    def template_delete(self, tid: str):
        tpls = self._store.data["templates"]
        tpls[:] = [t for t in tpls if t["id"] != tid]
        self._store.save()
        return tpls

    # ---------- бэкап ----------
    @api_call
    def backup_lot(self, node: int, offer: int, category: str = ""):
        import features
        return features.backup_lot(self._client(), int(node), int(offer), category)

    @api_call
    def backup_save(self, lots: list):
        """Сохраняет собранные лоты в файл через системный диалог «Сохранить»."""
        acc = self._acc()
        name = f"funpay-lots-{acc.get('username', 'backup')}-{time.strftime('%Y-%m-%d')}.json"
        path = self._window.create_file_dialog(webview.SAVE_DIALOG, save_filename=name,
                                               file_types=("Бэкап FunPay Lots (*.json)",))
        if not path:
            return None
        path = path if isinstance(path, str) else path[0]
        data = {"app": "FunPay Lots", "version": VERSION, "created": time.strftime("%Y-%m-%d %H:%M"),
                "account": acc.get("username"), "lots": lots}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    @api_call
    def backup_open(self):
        import features
        paths = self._window.create_file_dialog(webview.OPEN_DIALOG, file_types=("Бэкап FunPay Lots (*.json)",))
        if not paths:
            return None
        p = paths[0] if isinstance(paths, (list, tuple)) else paths
        try:
            data = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise FunPayError("Не удалось прочитать файл.")
        return {"path": p, "account": data.get("account"), "created": data.get("created"),
                "lots": features.check_backup(data)}

    @api_call
    def backup_restore(self, item: dict, inactive: bool = True):
        import features
        res = features.restore_lot(self._client(), item, bool(inactive))
        nodes = self._acc().setdefault("nodes", {})
        nodes.setdefault(str(int(item["node"])), item.get("category") or f"Раздел {item['node']}")
        self._store.save()
        return res

    # ---------- заказы, чаты, аренды ----------
    @api_call
    def orders(self, cont: str = "", state: str = ""):
        return self._client().orders(cont, state)

    @api_call
    def order(self, order_id: str):
        return self._client().order(order_id)

    @api_call
    def refund(self, order_id: str):
        return self._client().refund(order_id)

    @api_call
    def review_reply(self, order_id: str, text: str):
        return self._client().review_reply(order_id, text)

    @api_call
    def chats(self):
        return self._client().chats()

    @api_call
    def chat_history(self, chat_id: int):
        return self._client().chat_history(int(chat_id))

    @api_call
    def send_message(self, chat_id: int, text: str):
        return self._client().send_message(int(chat_id), text)

    @api_call
    def rentals(self):
        import features
        page = self._client().orders()
        return features.rentals(page["items"], time.time(), int(self._store.data.get("rental_bonus", 0)),
                                self._acc().get("rentals_extra"))

    @api_call
    def rental_adjust(self, order_id: str, minutes: int):
        """Добавляет (или убирает, если число отрицательное) минуты к сроку аренды по заказу.
        Возвращает итоговую ручную поправку в минутах."""
        order_id = str(order_id).strip().lstrip("#")
        if not re.fullmatch(r"[A-Za-z0-9]{4,16}", order_id):
            raise FunPayError("Неверный номер заказа.")
        try:
            delta = int(minutes)
        except (TypeError, ValueError):
            raise FunPayError("Укажите число минут.")
        acc = self._acc()
        extra = acc.setdefault("rentals_extra", {})
        total = max(-7 * 24 * 60, min(extra.get(order_id, 0) + delta, 30 * 24 * 60))
        if total:
            extra[order_id] = total
        else:
            extra.pop(order_id, None)
        # Срок изменился — напоминания «скоро закончится» и «закончилась» должны сработать заново.
        for key in ("rentals_done", "rentals_warned"):
            if order_id in acc.get(key, []):
                acc[key].remove(order_id)
        for k in list(extra)[:-300]:  # не копим поправки по давно закрытым заказам
            extra.pop(k, None)
        self._store.save()
        return total

    # ---------- аналитика ----------
    @api_call
    def stats(self, days: int = 30):
        import features
        return features.stats(self._client(), int(days))

    @api_call
    def competitors(self, node: int):
        import features
        return features.competitors(self._client(), int(node))

    # ---------- ответы с ИИ ----------
    @api_call
    def ai_chat_reply(self, chat_id: int, hint: str = ""):
        h = self._client().chat_history(int(chat_id))
        return self._ai().reply_chat(h["messages"][-30:], hint)

    @api_call
    def ai_review_reply(self, order_id: str, hint: str = ""):
        o = self._client().order(order_id)
        title = next((p["value"] for p in o["params"] if p["name"] == "Краткое описание"), "")
        return self._ai().reply_review(o["review"]["text"], o["review"]["rating"], title, hint)

    # ---------- финансы ----------
    @api_call
    def finance(self):
        return self._client().finance()

    @api_call
    def transactions(self, filter_: str = "", cont: str = ""):
        return self._client().transactions(filter_, cont)

    @api_call
    def withdraw_calc(self, currency: str, method: str, amount: str, wallet: str = "", bank: str = ""):
        return self._client().withdraw_calc(currency, method, amount, wallet, bank)

    @api_call
    def withdraw_preview(self, currency: str, method: str, wallet: str, amount: str, bank: str = ""):
        return self._client().withdraw(currency, method, wallet, amount, bank, confirm=False)

    @api_call
    def withdraw_confirm(self, currency: str, method: str, wallet: str, amount: str, bank: str = "",
                         twofactor: str = ""):
        return self._client().withdraw(currency, method, wallet, amount, bank, confirm=True, twofactor=twofactor)

    # ---------- нейросеть ----------
    def _ai(self):
        import ai  # SDK Anthropic грузится только когда нужен — быстрее старт
        return ai.AI(self._store.data.get("anthropic_key", ""), os.environ.get("FPL_ANTHROPIC_BASE_URL"))

    @api_call
    def ai_status(self):
        key = self._store.data.get("anthropic_key", "")
        return {"has_key": bool(key), "masked": (key[:10] + "…" + key[-4:]) if len(key) > 16 else "",
                "translator": self._store.data.get("translator", "auto"),
                "free_email": self._store.data.get("mymemory_email", "")}

    @api_call
    def set_translator(self, mode: str, email: str = ""):
        if mode not in ("auto", "free", "claude"):
            raise FunPayError("Неизвестный режим перевода.")
        email = (email or "").strip()
        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise FunPayError("Почта для переводчика указана неверно.")
        self._store.data["translator"] = mode
        if email:
            self._store.data["mymemory_email"] = email
        else:
            self._store.data.pop("mymemory_email", None)
        self._store.save()
        return True

    @api_call
    def ai_set_key(self, key: str):
        key = (key or "").strip()
        if not key:
            self._store.data.pop("anthropic_key", None)
            self._store.save()
            return {"has_key": False}
        import ai
        model = ai.AI(key, os.environ.get("FPL_ANTHROPIC_BASE_URL")).check_key()
        self._store.data["anthropic_key"] = key
        self._store.save()
        return {"has_key": True, "model": model}

    @api_call
    def ai_generate(self, brief: str, category: str, attributes: dict, current: dict,
                    with_payment_msg: bool = False, with_english: bool = True):
        return self._ai().generate(brief, category, attributes, current, bool(with_payment_msg), bool(with_english))

    @api_call
    def ai_translate(self, fields: dict):
        """Перевод на английский. Режим «auto»: нейросеть, если есть ключ, иначе бесплатный MyMemory."""
        mode = self._store.data.get("translator", "auto")
        has_key = bool(self._store.data.get("anthropic_key"))
        if mode == "claude" or (mode == "auto" and has_key):
            return {"engine": "claude", **self._ai().translate(fields)}
        import free_translate
        tr = free_translate.FreeTranslator(self._store.data.get("mymemory_email", ""))
        return {"engine": "free", **tr.translate(fields)}

    # ---------- обновления ----------
    @api_call
    def check_update(self):
        return self.find_update()

    def find_update(self) -> dict:
        """Спрашивает GitHub о последней версии (вызывают и окно, и фоновая проверка)."""
        self._update = updater.check(RUNTIME_VERSION)
        self._update["checked_at"] = time.time()
        return self._update

    @api_call
    def skip_update(self, version: str):
        self._store.data["skip_version"] = version
        self._store.save()
        return True

    @api_call
    def update_progress(self):
        return self._progress

    @api_call
    def install_update(self):
        if not self._update or not self._update.get("available"):
            raise updater.UpdateError("Нет доступного обновления.")
        self._progress = 0.0

        def prog(p):
            self._progress = p
        updater.install(self._update, prog)
        self._progress = 1.0
        # Новая версия уже запущена (или запустится после выхода) — закрываем текущую.
        threading.Timer(0.5, lambda: self._window and self._window.destroy()).start()
        return True

    @api_call
    def open_url(self, url: str):
        if url.startswith(("https://funpay.com/", "https://github.com/ivasantai/funpay-lots",
                           "https://console.anthropic.com/", "https://platform.claude.com/")):
            webbrowser.open(url)
        return True


def gui_backend() -> str | None:
    """На Linux собранная версия использует Qt (QtWebEngine): его можно положить внутрь приложения,
    в отличие от GTK/WebKit. На Windows/macOS pywebview сам выбирает Edge WebView2 / WebKit."""
    if sys.platform.startswith("linux"):
        return os.environ.get("PYWEBVIEW_GUI") or "qt"
    return None


def selftest() -> int:
    """Проверка сборки без окна: все модули и ресурсы на месте. Код возврата 0 — всё хорошо."""
    lines = [f"FunPay Lots {VERSION} {sys.platform} {updater.arch()} frozen={updater.is_frozen()}"]
    try:
        import anthropic
        import bs4
        import ai  # noqa: F401
        import free_translate  # noqa: F401
        import features  # noqa: F401
        import background  # noqa: F401
        if sys.platform == "win32":
            import pystray  # noqa: F401  (значок в трее)
        lines.append(f"anthropic {anthropic.__version__}, bs4 {bs4.__version__}")
        assert resource("ui/index.html").is_file() and resource("ui/icon.png").is_file(), "нет файлов интерфейса"
        if sys.platform == "win32":
            import webview.platforms.winforms  # noqa: F401  (тянет pythonnet и WebView2)
        elif sys.platform == "darwin":
            import webview.platforms.cocoa  # noqa: F401  (тянет pyobjc и WebKit)
        else:
            import webview.platforms.qt  # noqa: F401  (тянет PyQt6 и QtWebEngine)
        lines.append(f"update asset: {updater.asset_name()}")
        lines.append("OK")
        code = 0
    except Exception as e:  # noqa: BLE001
        lines.append(f"FAIL: {type(e).__name__}: {e}")
        code = 1
    text = "\n".join(lines)
    print(text)
    (config_dir() / "selftest.log").write_text(text + "\n", encoding="utf-8")
    return code


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if sys.platform.startswith("linux") and updater.is_frozen():
        # Песочница Chromium внутри QtWebEngine часто недоступна в упакованном приложении
        # (AppArmor/user namespaces). Окно показывает только локальный интерфейс приложения.
        os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    updater.cleanup_old()
    if "--update" in sys.argv:  # обновление без интерфейса; результат — в update.log рядом с config.json
        log = config_dir() / "update.log"
        try:
            info = updater.check(RUNTIME_VERSION)
            msg = f"current {info['current']}, latest {info['latest']}, available {info['available']}"
            if info["available"]:
                updater.install(info)
                msg += " -> installed, new version started"
        except Exception as e:  # noqa: BLE001
            msg = f"error: {e}"
        log.write_text(msg + "\n", encoding="utf-8")
        print(msg)
        return
    api = Api()
    api._window = webview.create_window(
        APP_NAME, html=page_html(), js_api=api,
        width=1240, height=800, min_size=(900, 600), background_color="#0f1115",
    )
    api._window.events.closing += api.on_closing

    def on_started():
        import background
        api._worker.start()
        background.start_tray(api, str(resource("ui/icon.png")))
    # Иконку окна pywebview берёт только на Linux (Qt). На Windows параметр ждёт .ico и падает на .png,
    # а иконка там и на macOS и так берётся из exe/.app.
    icon = str(resource("ui/icon.png")) if sys.platform.startswith("linux") else None
    webview.start(on_started, debug=bool(os.environ.get("FPL_DEBUG")), gui=gui_backend(), icon=icon)


def run():
    """Точка входа: ошибки запуска пишутся в app.log (у собранного приложения нет консоли)."""
    import logging
    log_path = config_dir() / "app.log"
    logging.basicConfig(filename=str(log_path), level=logging.WARNING, encoding="utf-8",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        logging.getLogger("funpay-lots").critical("Сбой при запуске:\n%s", traceback.format_exc())
        raise


if __name__ == "__main__":
    run()
