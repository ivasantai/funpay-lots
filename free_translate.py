"""Бесплатный перевод RU→EN через публичный API MyMemory (translated.net) — без ключа.

Лимиты MyMemory: до 500 байт на запрос; около 5 000 символов в день без почты и около 50 000,
если передать адрес почты (параметр `de`). Поэтому текст переводится по строкам (так же сохраняются
переносы), длинные строки режутся по предложениям, а строки без русских букв не отправляются вовсе.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

import requests

API = "https://api.mymemory.translated.net/get"
MAX_BYTES = 450
CYR = re.compile(r"[А-Яа-яЁё]")
# Маркеры списков, эмодзи и знаки по краям строки не отдаём переводчику — он их теряет или переставляет.
EDGES = re.compile(r"^([^\w]*)(.*?)([^\w]*)$", re.S)
FIELDS = ("summary", "desc", "payment_msg")


class FreeTranslateError(Exception):
    pass


def _chunks(line: str) -> list[str]:
    """Режет строку на куски не длиннее MAX_BYTES байт в UTF-8 — по предложениям, затем по словам."""
    if len(line.encode()) <= MAX_BYTES:
        return [line]
    parts, cur = [], ""
    for piece in re.split(r"(?<=[.!?…;])\s+|\s+", line):
        cand = f"{cur} {piece}" if cur else piece
        if len(cand.encode()) <= MAX_BYTES:
            cur = cand
        else:
            if cur:
                parts.append(cur)
            while len(piece.encode()) > MAX_BYTES:  # очень длинное «слово»
                cut = MAX_BYTES // 4
                parts.append(piece[:cut])
                piece = piece[cut:]
            cur = piece
    if cur:
        parts.append(cur)
    return parts


class FreeTranslator:
    def __init__(self, email: str = ""):
        self.email = (email or "").strip()
        self.s = requests.Session()
        self.s.headers["User-Agent"] = "FunPayLots"

    def _one(self, text: str) -> str:
        params = {"q": text, "langpair": "ru|en"}
        if self.email:
            params["de"] = self.email
        try:
            r = self.s.get(API, params=params, timeout=20)
        except requests.RequestException as e:
            raise FreeTranslateError(f"Нет связи с бесплатным переводчиком: {e}") from e
        try:
            j = r.json()
        except ValueError:
            raise FreeTranslateError(f"Бесплатный переводчик ответил ошибкой ({r.status_code}).")
        out = (j.get("responseData") or {}).get("translatedText") or ""
        status = str(j.get("responseStatus"))
        if j.get("quotaFinished") or "MYMEMORY WARNING" in out.upper() or status == "429":
            raise FreeTranslateError("Дневной лимит бесплатного перевода исчерпан. Попробуйте завтра, "
                                     "укажите почту в ⚙ (лимит станет в 10 раз больше) или добавьте ключ нейросети.")
        if status != "200" or not out:
            raise FreeTranslateError(f"Бесплатный переводчик не смог перевести текст ({j.get('responseDetails') or status}).")
        return out

    def translate_text(self, text: str, pool: ThreadPoolExecutor, cache: dict) -> str:
        lines = (text or "").split("\n")
        jobs = {}
        for line in lines:
            core = line.strip()
            if core and CYR.search(core) and core not in cache and core not in jobs:
                prefix, middle, suffix = EDGES.match(core).groups()
                jobs[core] = (prefix, suffix, [pool.submit(self._one, c) for c in _chunks(middle)])
        for core, (prefix, suffix, futs) in jobs.items():
            tr = " ".join(f.result() for f in futs).strip()
            if suffix and tr and tr[-1] == suffix[0]:  # переводчик сам добавил тот же знак
                tr = tr[:-1]
            cache[core] = prefix + tr + suffix
        out = []
        for line in lines:
            core = line.strip()
            if core in cache:
                lead = line[: len(line) - len(line.lstrip())]
                trail = line[len(line.rstrip()):]
                out.append(lead + cache[core] + trail)
            else:
                out.append(line)
        return "\n".join(out)

    def translate(self, fields: dict) -> dict:
        src = {k: (fields or {}).get(k) or "" for k in FIELDS}
        if not any(CYR.search(v) for v in src.values()):
            raise FreeTranslateError("Нечего переводить: в русских полях нет текста на русском.")
        cache: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            res = {k: self.translate_text(v, pool, cache) if v.strip() else "" for k, v in src.items()}
        res["summary"] = " ".join(res["summary"].split())  # краткое описание — одна строка
        return res
