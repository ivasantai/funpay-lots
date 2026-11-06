"""Генерирует иконки приложения из assets/icon-source.* (квадратная картинка).

    python tools/make_icons.py

Результат:
  assets/icon.ico   — Windows (16…256 px, скруглённые углы)
  assets/icon.icns  — macOS (по гайдлайнам Big Sur+: скругление и поле вокруг)
  assets/icon.png   — 1024 px, для README/документации
  ui/icon.png       — 256 px, логотип в интерфейсе
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SRC = next(ASSETS.glob("icon-source.*"))
SS = 4  # суперсэмплинг для гладких краёв маски


def rounded(img: Image.Image, radius_ratio: float) -> Image.Image:
    size = img.size[0]
    big = size * SS
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * radius_ratio), fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask.resize((size, size), Image.LANCZOS))
    return out


def main():
    src = Image.open(SRC).convert("RGB")
    side = min(src.size)
    src = src.crop(((src.width - side) // 2, (src.height - side) // 2,
                    (src.width + side) // 2, (src.height + side) // 2)).resize((1024, 1024), Image.LANCZOS)

    win = rounded(src, 0.18)
    win.save(ASSETS / "icon.png")
    win.save(ASSETS / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    win.resize((256, 256), Image.LANCZOS).save(ROOT / "ui" / "icon.png", optimize=True)

    # macOS: плитка 824×824 со скруглением ~22.5% по центру холста 1024×1024
    tile = rounded(src.resize((824, 824), Image.LANCZOS), 0.225)
    mac = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    mac.paste(tile, (100, 100), tile)
    mac.save(ASSETS / "icon.icns")
    print("ok:", ", ".join(p.name for p in [ASSETS / "icon.ico", ASSETS / "icon.icns", ASSETS / "icon.png"]), "+ ui/icon.png")


if __name__ == "__main__":
    main()
