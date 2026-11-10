# PyInstaller: pyinstaller funpay_lots.spec
# Windows -> dist/FunPayLots.exe
# macOS   -> dist/FunPay Lots.app (архитектура — как у Python, на котором собирают: arm64 или x86_64)
# Linux   -> dist/FunPayLots (один исполняемый файл, интерфейс на QtWebEngine)
import platform
import sys

VERSION = "1.7.0"

a = Analysis(
    ["app.py"],
    pathex=[],
    datas=[("ui/index.html", "ui"), ("ui/icon.png", "ui"), ("ui/i18n_en.json", "ui")],
    hiddenimports=["ai", "free_translate", "features", "background"]
    + (["pystray._win32"] if sys.platform == "win32" else []),  # импортируются лениво внутри функций
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    arch = "arm64" if platform.machine() == "arm64" else "x86_64"
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FunPay Lots",
              console=False, target_arch=arch, icon="assets/icon.icns")
    coll = COLLECT(exe, a.binaries, a.datas, name="FunPay Lots")
    app = BUNDLE(coll, name="FunPay Lots.app", icon="assets/icon.icns",
                 bundle_identifier="com.ivasantai.funpaylots",
                 info_plist={"NSHighResolutionCapable": True, "LSMinimumSystemVersion": "11.0",
                             "CFBundleShortVersionString": VERSION, "CFBundleVersion": VERSION})
elif sys.platform == "win32":
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="FunPayLots",
              console=False, upx=False, icon="assets/icon.ico")
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="FunPayLots",
              console=False, upx=False, strip=False)
