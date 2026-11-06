# PyInstaller: pyinstaller funpay_lots.spec
# Windows -> dist/FunPayLots.exe ; macOS -> dist/FunPay Lots.app
import sys

block_cipher = None

a = Analysis(
    ["app.py"],
    pathex=[],
    datas=[("ui/index.html", "ui")],
    hiddenimports=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FunPay Lots",
              console=False, target_arch="arm64")
    coll = COLLECT(exe, a.binaries, a.datas, name="FunPay Lots")
    app = BUNDLE(coll, name="FunPay Lots.app", bundle_identifier="com.ivasantai.funpaylots",
                 info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "1.0.0"})
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="FunPayLots",
              console=False, upx=False)
