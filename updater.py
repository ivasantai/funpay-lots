"""Автообновление из GitHub Releases.

Windows: скачивает новый FunPayLots.exe рядом со старым, переименовывает запущенный exe в *.old
(Windows это позволяет), ставит новый на его место и перезапускает приложение.
macOS: скачивает zip, распаковывает через ditto (сохраняет права и симлинки), подменяет .app
и перезапускает его.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

REPO = "ivasantai/funpay-lots"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
WIN_ASSET = "FunPayLots.exe"
MAC_ASSET = "FunPayLots-macos-arm64.zip"


class UpdateError(Exception):
    pass


def parse_version(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def asset_name() -> str | None:
    if sys.platform == "win32":
        return WIN_ASSET
    if sys.platform == "darwin":
        return MAC_ASSET
    return None


def check(current: str) -> dict:
    try:
        r = requests.get(API, headers={"Accept": "application/vnd.github+json", "User-Agent": "FunPayLots-updater"},
                         timeout=15)
    except requests.RequestException as e:
        raise UpdateError(f"Не удалось проверить обновления: {e}") from e
    if r.status_code == 404:
        raise UpdateError("Релизы не найдены (репозиторий недоступен).")
    if r.status_code != 200:
        raise UpdateError(f"GitHub ответил {r.status_code} при проверке обновлений.")
    rel = r.json()
    latest = rel.get("tag_name", "").lstrip("v")
    name = asset_name()
    asset = next((a for a in rel.get("assets", []) if a.get("name") == name), None)
    return {
        "current": current,
        "latest": latest,
        "available": parse_version(latest) > parse_version(current),
        "notes": rel.get("body") or "",
        "url": rel.get("html_url") or RELEASES_PAGE,
        "download": asset["browser_download_url"] if asset else "",
        "size": asset.get("size", 0) if asset else 0,
        # Сам себя обновлять умеет только собранный exe/app; из исходников — просто ссылка на релиз.
        "can_install": bool(asset and is_frozen()),
    }


def _download(url: str, dest: Path, progress=None):
    try:
        with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "FunPayLots-updater"}) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(256 * 1024):
                    f.write(chunk)
                    done += len(chunk)
                    if progress and total:
                        progress(done / total)
    except requests.RequestException as e:
        raise UpdateError(f"Не удалось скачать обновление: {e}") from e


def cleanup_old():
    """Удаляет остатки прошлого обновления (вызывать при старте)."""
    if is_frozen() and sys.platform == "win32":
        old = Path(sys.executable).with_suffix(".old")
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass


def install(info: dict, progress=None) -> None:
    """Скачивает и ставит обновление, затем запускает новую версию. После вызова приложение нужно закрыть."""
    if not info.get("can_install"):
        raise UpdateError("Автоустановка доступна только в собранной версии приложения.")
    if sys.platform == "win32":
        _install_windows(info, progress)
    elif sys.platform == "darwin":
        _install_macos(info, progress)
    else:
        raise UpdateError("Автообновление на этой ОС не поддерживается.")


def _install_windows(info: dict, progress):
    exe = Path(sys.executable)
    new = exe.with_name(exe.stem + ".new.exe")
    old = exe.with_suffix(".old")
    try:
        _download(info["download"], new, progress)
        if new.stat().st_size < 1_000_000:
            raise UpdateError("Скачанный файл повреждён.")
        old.unlink(missing_ok=True)
        exe.rename(old)          # запущенный exe можно переименовать, но не удалить
        new.rename(exe)
    except PermissionError as e:
        new.unlink(missing_ok=True)
        if old.exists() and not exe.exists():
            old.rename(exe)
        raise UpdateError(f"Нет прав на запись в папку {exe.parent}. Переместите приложение, например, на рабочий стол.") from e
    except Exception:
        new.unlink(missing_ok=True)
        if old.exists() and not exe.exists():
            old.rename(exe)
        raise
    _relaunch_windows(exe)


def _relaunch_windows(exe: Path):
    """Запускает новую версию так, чтобы она пережила выход текущего процесса.
    Загрузчик PyInstaller держит процесс в job object, который при закрытии убивает всех потомков,
    поэтому новый процесс выводим из job (CREATE_BREAKAWAY_FROM_JOB), а если job этого не разрешает —
    запускаем через explorer.exe, как обычный двойной клик."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("_MEI") and k != "_PYI_APPLICATION_HOME_DIR"}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"  # новый exe должен распаковаться заново, а не взять нашу папку
    base = getattr(subprocess, "DETACHED_PROCESS", 0x8) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    try:
        subprocess.Popen([str(exe)], creationflags=base | breakaway, close_fds=True, env=env, cwd=str(exe.parent))
    except OSError:
        subprocess.Popen(["explorer.exe", str(exe)], close_fds=True, env=env)


def _install_macos(info: dict, progress):
    exe = Path(sys.executable).resolve()
    app = next((p for p in exe.parents if p.suffix == ".app"), None)
    if not app:
        raise UpdateError("Не удалось найти .app приложения.")
    tmp = Path(tempfile.mkdtemp(prefix="funpaylots-upd-"))
    zip_path = tmp / MAC_ASSET
    _download(info["download"], zip_path, progress)
    out = tmp / "unpacked"
    subprocess.run(["ditto", "-x", "-k", str(zip_path), str(out)], check=True)
    new_app = next(out.glob("*.app"), None)
    if not new_app:
        raise UpdateError("В архиве обновления нет приложения.")
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(new_app)], check=False)
    backup = app.with_name(app.name + ".old")
    try:
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
        app.rename(backup)
        subprocess.run(["ditto", str(new_app), str(app)], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        if backup.exists() and not app.exists():
            backup.rename(app)
        raise UpdateError(f"Не удалось заменить приложение ({e}). Проверьте права на папку {app.parent}.") from e
    # Ждём выхода текущего процесса, удаляем старую копию и открываем новую.
    script = f'while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.3; done; rm -rf "{backup}" "{tmp}"; open "{app}"'
    subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
