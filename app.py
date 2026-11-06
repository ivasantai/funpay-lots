"""FunPay Lots — десктоп-приложение для управления лотами FunPay."""
from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import webview

from funpay_client import FunPayClient, FunPayError

APP_NAME = "FunPay Lots"
VERSION = "1.0.0"


def resource(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


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
        except FunPayError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return {"ok": False, "error": f"Внутренняя ошибка: {e}"}
    wrapper.__name__ = fn.__name__
    return wrapper


class Api:
    def __init__(self):
        self.store = Store()
        self.client: FunPayClient | None = None

    def _client(self) -> FunPayClient:
        if not self.client:
            raise FunPayError("Сначала войдите по ключу.")
        return self.client

    @api_call
    def state(self):
        return {"has_key": bool(self.store.data.get("golden_key")), "version": VERSION}

    @api_call
    def login(self, key: str | None = None, remember: bool = True):
        key = key or self.store.data.get("golden_key")
        if not key:
            raise FunPayError("Введите golden_key.")
        client = FunPayClient(key)
        acc = client.login()
        self.client = client
        if remember:
            self.store.data["golden_key"] = key.strip()
        else:
            self.store.data.pop("golden_key", None)
        self.store.save()
        return {"id": acc.id, "username": acc.username, "balance": acc.balance}

    @api_call
    def logout(self):
        self.client = None
        self.store.data.pop("golden_key", None)
        self.store.save()
        return True

    @api_call
    def lots(self):
        c = self._client()
        nodes: dict[int, str] = {int(k): v for k, v in self.store.data["nodes"].items()}
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
                self.store.data["nodes"][str(n)] = name
            cats.append({"node": n, "name": name, "lots": lots, "error": err})
        self.store.save()
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
        if category_name or key not in self.store.data["nodes"]:
            self.store.data["nodes"][key] = category_name or self.store.data["nodes"].get(key) or f"Раздел {node}"
            self.store.save()
        return res

    @api_call
    def delete(self, node: int, offer: int):
        return self._client().delete(int(node), int(offer))

    @api_call
    def set_active(self, node: int, offer: int, active: bool):
        return self._client().set_active(int(node), int(offer), bool(active))

    @api_call
    def forget_category(self, node: int):
        self.store.data["nodes"].pop(str(int(node)), None)
        self.store.save()
        return True

    @api_call
    def open_url(self, url: str):
        if url.startswith("https://funpay.com/"):
            webbrowser.open(url)
        return True


def main():
    api = Api()
    webview.create_window(
        APP_NAME, url=str(resource("ui/index.html")), js_api=api,
        width=1240, height=800, min_size=(900, 600), background_color="#0f1115",
    )
    webview.start(debug=bool(os.environ.get("FPL_DEBUG")))


if __name__ == "__main__":
    main()
