"""Автообновление из GitHub Releases.

Windows: новый exe скачивается рядом со старым; запущенный exe переносится во временную папку
(Windows разрешает перенос, но не удаление), новый встаёт на его место и запускается.
macOS: zip распаковывается через ditto, старый .app уходит во временную папку, новый копируется
на его место. Если macOS запустила приложение из «карантинной» копии (App Translocation),
обновление ставится в настоящую папку приложения или в «Программы».
Linux: из tar.gz берётся новый бинарник и атомарно заменяет старый (os.replace).
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path

import requests

REPO = "ivasantai/funpay-lots"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
OLD_PREFIX = "FunPayLots-old-"


class UpdateError(Exception):
    pass


def parse_version(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def arch() -> str:
    m = platform.machine().lower()
    return "arm64" if m in ("arm64", "aarch64") else "x86_64"


def asset_name() -> str | None:
    if sys.platform == "win32":
        return "FunPayLots.exe"
    if sys.platform == "darwin":
        return f"FunPayLots-macos-{arch()}.zip"
    if sys.platform.startswith("linux"):
        return f"FunPayLots-linux-{arch()}.tar.gz"
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
        # Сам себя обновлять умеет только собранное приложение; из исходников — просто ссылка на релиз.
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


def _fresh_env() -> dict:
    """Окружение для запуска новой версии: без переменных распаковщика PyInstaller текущего процесса."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("_MEI") and not k.startswith("_PYI")}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


# ---------- уборка после прошлого обновления ----------

def _old_candidates() -> list[Path]:
    exe = Path(sys.executable)
    items = [exe.with_suffix(".old"), exe.with_name("." + exe.stem + ".old")]
    try:
        items += list(Path(tempfile.gettempdir()).glob(OLD_PREFIX + "*"))
    except OSError:
        pass
    return items


def _remove(p: Path) -> bool:
    try:
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
        return True
    except OSError:
        return False


def cleanup_old():
    """Удаляет остатки прошлого обновления. Старый процесс может ещё завершаться и держать файл,
    поэтому неудачные попытки повторяются в фоне до минуты."""
    if not is_frozen():
        return
    left = [p for p in _old_candidates() if not _remove(p)]
    if not left:
        return

    def retry():
        pending = left
        for _ in range(30):
            time.sleep(2)
            pending = [p for p in pending if not _remove(p)]
            if not pending:
                return
    threading.Thread(target=retry, daemon=True).start()


# ---------- установка ----------

def install(info: dict, progress=None) -> None:
    """Скачивает и ставит обновление, затем запускает новую версию. После вызова приложение нужно закрыть."""
    if not info.get("can_install"):
        raise UpdateError("Автоустановка доступна только в собранной версии приложения.")
    if sys.platform == "win32":
        _install_windows(info, progress)
    elif sys.platform == "darwin":
        _install_macos(info, progress)
    elif sys.platform.startswith("linux"):
        _install_linux(info, progress)
    else:
        raise UpdateError("Автообновление на этой ОС не поддерживается.")


def _same_drive(a: Path, b: Path) -> bool:
    return os.path.splitdrive(str(a.resolve()))[0].lower() == os.path.splitdrive(str(b.resolve()))[0].lower()


def _install_windows(info: dict, progress):
    exe = Path(sys.executable)
    new = exe.with_name("." + exe.stem + ".new.exe")
    tmpdir = Path(tempfile.gettempdir())
    # Запущенный exe нельзя удалить, но можно перенести. Уносим его во временную папку (если она на том же
    # диске), чтобы рядом с приложением не оставалось .old; иначе — скрытый файл рядом.
    if _same_drive(exe, tmpdir):
        old = tmpdir / f"{OLD_PREFIX}{int(time.time())}.exe"
    else:
        old = exe.with_name("." + exe.stem + ".old")
    try:
        _download(info["download"], new, progress)
        if new.stat().st_size < 1_000_000:
            raise UpdateError("Скачанный файл повреждён.")
        _remove(old)
        os.rename(exe, old)
        os.rename(new, exe)
    except PermissionError as e:
        _remove(new)
        if old.exists() and not exe.exists():
            os.rename(old, exe)
        raise UpdateError(f"Нет прав на запись в папку {exe.parent}. Переместите приложение, например, на рабочий стол.") from e
    except Exception:
        _remove(new)
        if old.exists() and not exe.exists():
            os.rename(old, exe)
        raise
    if old.parent == exe.parent:
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(old), 0x2)  # FILE_ATTRIBUTE_HIDDEN
        except Exception:
            pass
    _relaunch_windows(exe)


def _relaunch_windows(exe: Path):
    """Запускает новую версию так, чтобы она пережила выход текущего процесса.
    Загрузчик PyInstaller держит процесс в job object, который при закрытии убивает всех потомков,
    поэтому новый процесс выводим из job (CREATE_BREAKAWAY_FROM_JOB), а если job этого не разрешает —
    запускаем через explorer.exe, как обычный двойной клик."""
    env = _fresh_env()
    base = getattr(subprocess, "DETACHED_PROCESS", 0x8) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
    breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
    try:
        subprocess.Popen([str(exe)], creationflags=base | breakaway, close_fds=True, env=env, cwd=str(exe.parent))
    except OSError:
        subprocess.Popen(["explorer.exe", str(exe)], close_fds=True, env=env)


def _untranslocate(app: Path) -> Path | None:
    """Если macOS запустила приложение из App Translocation (read-only копия для файлов с карантином),
    возвращает настоящий путь к .app через Security.framework. Иначе None."""
    if "/AppTranslocation/" not in str(app):
        return None
    try:
        import ctypes
        import ctypes.util
        cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
        sec = ctypes.cdll.LoadLibrary(ctypes.util.find_library("Security"))
        cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
        cf.CFURLGetFileSystemRepresentation.restype = ctypes.c_bool
        cf.CFURLGetFileSystemRepresentation.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_char_p, ctypes.c_long]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        sec.SecTranslocateCreateOriginalPathForURL.restype = ctypes.c_void_p
        sec.SecTranslocateCreateOriginalPathForURL.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        raw = str(app).encode()
        url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), True)
        if not url:
            return None
        orig = sec.SecTranslocateCreateOriginalPathForURL(url, None)
        cf.CFRelease(url)
        if not orig:
            return None
        buf = ctypes.create_string_buffer(4096)
        ok = cf.CFURLGetFileSystemRepresentation(orig, True, buf, len(buf))
        cf.CFRelease(orig)
        p = Path(buf.value.decode()) if ok and buf.value else None
        return p if p and "/AppTranslocation/" not in str(p) else None
    except Exception:
        return None


def _writable_dir(d: Path) -> bool:
    return d.is_dir() and os.access(d, os.W_OK)


def _install_macos(info: dict, progress):
    exe = Path(sys.executable).resolve()
    running = next((p for p in exe.parents if p.suffix == ".app"), None)
    if not running:
        raise UpdateError("Не удалось найти .app приложения.")

    # Куда ставить: обычно на место запущенного .app. Если он запущен из App Translocation (read-only),
    # — в настоящую папку приложения, а если её не узнать или туда нельзя писать — в «Программы».
    target = running
    if "/AppTranslocation/" in str(running) or not _writable_dir(running.parent):
        orig = _untranslocate(running)
        if orig and _writable_dir(orig.parent):
            target = orig
        elif _writable_dir(Path("/Applications")):
            target = Path("/Applications") / running.name
        else:
            user_apps = Path.home() / "Applications"
            user_apps.mkdir(exist_ok=True)
            target = user_apps / running.name

    tmp = Path(tempfile.mkdtemp(prefix=OLD_PREFIX))
    zip_path = tmp / "update.zip"
    _download(info["download"], zip_path, progress)
    out = tmp / "unpacked"
    subprocess.run(["ditto", "-x", "-k", str(zip_path), str(out)], check=True)
    new_app = next(out.glob("*.app"), None)
    if not new_app:
        raise UpdateError("В архиве обновления нет приложения.")

    backup = None
    try:
        if target.exists():
            # Старую копию уносим во временную папку (тот же том — это простое переименование);
            # если не вышло — прячем рядом (имя с точкой не видно в Finder) и удаляем после выхода.
            backup = tmp / "previous.app"
            try:
                os.rename(target, backup)
            except OSError:
                backup = target.with_name("." + target.name + ".old")
                _remove(backup)
                os.rename(target, backup)
        subprocess.run(["ditto", str(new_app), str(target)], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        if backup and backup.exists() and not target.exists():
            os.rename(backup, target)
        raise UpdateError(f"Не удалось установить обновление в {target.parent} ({e}). "
                          f"Перенесите приложение в «Программы» и попробуйте снова.") from e
    # Без карантина macOS не будет снова запускать приложение из read-only копии.
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(target)], check=False)
    script = (f'while kill -0 {os.getpid()} 2>/dev/null; do sleep 0.3; done; '
              f'rm -rf "{tmp}"' + (f' "{backup}"' if backup else "") + f'; open "{target}"')
    subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _install_linux(info: dict, progress):
    exe = Path(sys.executable).resolve()
    if not _writable_dir(exe.parent):
        raise UpdateError(f"Нет прав на запись в папку {exe.parent}.")
    tmp = Path(tempfile.mkdtemp(prefix=OLD_PREFIX))
    try:
        archive = tmp / "update.tar.gz"
        _download(info["download"], archive, progress)
        with tarfile.open(archive) as tf:
            member = next((m for m in tf.getmembers() if m.isfile() and Path(m.name).name == "FunPayLots"), None)
            if not member:
                raise UpdateError("В архиве обновления нет приложения.")
            src = tf.extractfile(member)
            new = exe.with_name("." + exe.name + ".new")
            with open(new, "wb") as f:
                shutil.copyfileobj(src, f)
        os.chmod(new, 0o755)
        os.replace(new, exe)  # атомарно; запущенный процесс продолжает работать со старым inode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    subprocess.Popen([str(exe)], start_new_session=True, env=_fresh_env(), cwd=str(exe.parent),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
