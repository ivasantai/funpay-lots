"""FunPay Lots — десктоп-приложение для управления лотами FunPay."""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import webview

import updater
from funpay_client import FunPayClient, FunPayError

APP_NAME = "FunPay Lots"
VERSION = "1.5.0"
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
        self.data.setdefault("nodes", {})  # node -> name (разделы, где были лоты)

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


class Api:
    def __init__(self):
        self._store = Store()
        self._fp: FunPayClient | None = None
        self._window = None
        self._update: dict | None = None
        self._progress = 0.0

    def _client(self) -> FunPayClient:
        if not self._fp:
            raise FunPayError("Сначала войдите по ключу.")
        return self._fp

    @api_call
    def state(self):
        return {"has_key": bool(self._store.data.get("golden_key")), "version": RUNTIME_VERSION,
                "skipped": self._store.data.get("skip_version", "")}

    @api_call
    def login(self, key: str | None = None, remember: bool = True):
        key = key or self._store.data.get("golden_key")
        if not key:
            raise FunPayError("Введите golden_key.")
        client = FunPayClient(key)
        acc = client.login()
        self._fp = client
        if remember:
            self._store.data["golden_key"] = key.strip()
        else:
            self._store.data.pop("golden_key", None)
        self._store.save()
        return {"id": acc.id, "username": acc.username, "balance": acc.balance}

    @api_call
    def logout(self):
        self._fp = None
        self._store.data.pop("golden_key", None)
        self._store.save()
        return True

    @api_call
    def lots(self):
        c = self._client()
        nodes: dict[int, str] = {int(k): v for k, v in self._store.data["nodes"].items()}
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
                self._store.data["nodes"][str(n)] = name
            cats.append({"node": n, "name": name, "lots": lots, "error": err})
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
        if category_name or key not in self._store.data["nodes"]:
            self._store.data["nodes"][key] = category_name or self._store.data["nodes"].get(key) or f"Раздел {node}"
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
        self._store.data["nodes"].pop(str(int(node)), None)
        self._store.save()
        return True

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
        self._update = updater.check(RUNTIME_VERSION)
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
    # Иконку окна pywebview берёт только на Linux (Qt). На Windows параметр ждёт .ico и падает на .png,
    # а иконка там и на macOS и так берётся из exe/.app.
    icon = str(resource("ui/icon.png")) if sys.platform.startswith("linux") else None
    webview.start(debug=bool(os.environ.get("FPL_DEBUG")), gui=gui_backend(), icon=icon)


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
