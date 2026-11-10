"""Перевод сообщений Python-части (ошибки, уведомления) на английский.

Словарь общий с интерфейсом — ui/i18n_en.json (собирается tools/i18n_build.py). Логика та же, что в tr() из
ui/index.html: точное совпадение → шаблон (группы $1… переводятся рекурсивно) → разбор по « • », « · », «: ».
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CYR = re.compile(r"[А-Яа-яЁё]")
SEPARATORS = (" • ", " · ", " — ", ": ")
_data: dict | None = None


def _load() -> dict:
    global _data
    if _data is None:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        try:
            raw = json.loads((base / "ui" / "i18n_en.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {"exact": {}, "patterns": []}
        _data = {"exact": raw["exact"], "patterns": [(re.compile(p), r) for p, r in raw["patterns"]]}
    return _data


def tr(text: str, lang: str = "en", _depth: int = 0) -> str:
    if lang != "en" or not text or not CYR.search(text) or _depth > 6:
        return text
    d = _load()
    core = " ".join(text.split())  # переносы и лишние пробелы не мешают поиску
    lead, trail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    if core in d["exact"]:
        return lead + d["exact"][core] + trail
    for rx, rep in d["patterns"]:
        m = rx.fullmatch(core)
        if m:
            out = re.sub(r"\$(\d)", lambda g: tr(m.group(int(g.group(1))) or "", lang, _depth + 1), rep)
            return lead + out + trail
    for sep in SEPARATORS:
        if sep in core:
            head, _, rest = core.partition(sep) if sep == ": " else (None, None, None)
            parts = [head, rest] if sep == ": " else core.split(sep)
            translated = [tr(p, lang, _depth + 1) for p in parts]
            if translated != parts:
                return lead + sep.join(translated) + trail
    return text
