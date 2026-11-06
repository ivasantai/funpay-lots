"""Нейросеть для описаний лотов: генерация текста и перевод на английский (Claude API).

Ключ API пользователь вводит в настройках приложения; он хранится локально в config.json.
"""
from __future__ import annotations

import json

import anthropic

MODEL = "claude-opus-5-5"
# Если классификаторы безопасности откажут, API сам перезапустит запрос на рекомендованной модели.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

FIELDS = ("summary", "desc", "payment_msg")

SYSTEM = """Ты — опытный продавец и копирайтер на маркетплейсе FunPay (игровые ценности, аккаунты, подписки, услуги).
Пишешь тексты лотов, которые понятны покупателю и продают.

Правила FunPay, которые нельзя нарушать:
- никаких контактов вне FunPay (Telegram, Discord, почта, телефон), ссылок на сторонние сайты и призывов писать вне FunPay;
- не обещай того, чего нет во вводных; не выдумывай цены, сроки и гарантии — бери только из вводных продавца;
- без капса на весь текст и без оскорблений конкурентов.

Поля лота:
- summary — «Краткое описание»: одна строка, заголовок лота в списке, до ~100 символов. Главное — что продаётся и ключевое преимущество.
- desc — «Подробное описание»: что получает покупатель, условия, как проходит выдача, важные оговорки. Короткие абзацы или списки, переносы строк.
- payment_msg — «Сообщение покупателю после оплаты»: что делать дальше, как получить товар. Пусто, если продавец об этом не просил.

Если продавец дал пример своего текста — сохраняй его стиль (эмодзи, оформление, тон)."""

TRANSLATE_SYSTEM = """You translate FunPay marketplace listings from Russian to English.
- Natural, fluent English that a gamer/buyer would expect on a marketplace; not word-for-word.
- Keep emojis, line breaks, list markers, numbers, prices, product and game names exactly as they are.
- Do not add or remove information. Do not add contacts or links.
- summary stays a single line. Empty input field -> empty output field."""


def _schema(keys) -> dict:
    return {
        "type": "object",
        "properties": {k: {"type": "string"} for k in keys},
        "required": list(keys),
        "additionalProperties": False,
    }


class AIError(Exception):
    pass


class AI:
    def __init__(self, api_key: str, base_url: str | None = None):
        if not (api_key or "").strip():
            raise AIError("Укажите ключ Anthropic API в настройках (⚙).")
        self.client = anthropic.Anthropic(api_key=api_key.strip(), base_url=base_url, max_retries=2, timeout=180)

    def check_key(self) -> str:
        """Проверка ключа без генерации (бесплатно)."""
        try:
            m = self.client.models.retrieve(MODEL)
            return m.display_name or MODEL
        except anthropic.AuthenticationError:
            raise AIError("Ключ не подошёл: Anthropic его не принял.")
        except anthropic.PermissionDeniedError:
            raise AIError("У ключа нет доступа к модели.")
        except anthropic.APIConnectionError:
            raise AIError("Нет связи с api.anthropic.com.")
        except anthropic.APIStatusError as e:
            raise AIError(f"Ошибка Anthropic API ({e.status_code}): {e.message}")

    def _ask(self, system: str, prompt: str, keys, effort: str) -> dict:
        try:
            resp = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                system=system,
                output_config={"effort": effort, "format": {"type": "json_schema", "schema": _schema(keys)}},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError:
            raise AIError("Ключ Anthropic не подошёл — проверьте его в настройках (⚙).")
        except anthropic.PermissionDeniedError:
            raise AIError("У ключа Anthropic нет доступа к модели.")
        except anthropic.RateLimitError:
            raise AIError("Слишком много запросов к нейросети — подождите минуту.")
        except anthropic.BadRequestError as e:
            msg = e.message or ""
            if "credit" in msg.lower() or "balance" in msg.lower():
                raise AIError("На аккаунте Anthropic закончились средства — пополните баланс в console.anthropic.com.")
            raise AIError(f"Нейросеть отклонила запрос: {msg}")
        except anthropic.APIConnectionError:
            raise AIError("Нет связи с api.anthropic.com.")
        except anthropic.APIStatusError as e:
            raise AIError(f"Ошибка Anthropic API ({e.status_code}): {e.message}")

        if resp.stop_reason == "refusal":
            raise AIError("Нейросеть отказалась писать такой текст. Переформулируйте вводные.")
        if resp.stop_reason == "max_tokens":
            raise AIError("Ответ получился слишком длинным. Сократите вводные.")
        texts = [b.text for b in resp.content if b.type == "text"]
        if not texts:
            raise AIError("Нейросеть вернула пустой ответ.")
        try:
            data = json.loads(texts[-1])
        except ValueError:
            raise AIError("Нейросеть вернула ответ в неожиданном формате. Попробуйте ещё раз.")
        return {k: str(data.get(k) or "").strip() for k in keys}

    def generate(self, brief: str, category: str, attributes: dict, current: dict,
                 with_payment_msg: bool, with_english: bool) -> dict:
        if not (brief or "").strip() and not any((current or {}).values()):
            raise AIError("Опишите, что продаёте: пара фраз о товаре, условиях и выдаче.")
        attrs = "\n".join(f"- {k}: {v}" for k, v in (attributes or {}).items() if v) or "—"
        cur = "\n\n".join(f"[{k}]\n{v}" for k, v in (current or {}).items() if v) or "—"
        prompt = (
            f"Раздел FunPay: {category or 'не указан'}\n"
            f"Параметры лота из формы:\n{attrs}\n\n"
            f"Вводные продавца:\n{brief.strip() or '—'}\n\n"
            f"Текущий текст лота (пример стиля; улучшай, не теряя фактов):\n{cur}\n\n"
            f"Напиши summary и desc на русском. "
            + ("Напиши и payment_msg. " if with_payment_msg else "payment_msg оставь пустым. ")
            + ("Также дай английские версии полей в summary_en, desc_en, payment_msg_en по тем же правилам." if with_english else "")
        )
        keys = list(FIELDS) + ([f"{k}_en" for k in FIELDS] if with_english else [])
        out = self._ask(SYSTEM, prompt, keys, effort="medium")
        if not with_payment_msg:
            out["payment_msg"] = ""
            out.pop("payment_msg_en", None)
        return out

    def translate(self, fields: dict) -> dict:
        src = {k: (fields or {}).get(k, "") for k in FIELDS}
        if not any(v.strip() for v in src.values()):
            raise AIError("Нечего переводить: русские поля пустые.")
        prompt = "Translate each field to English:\n\n" + json.dumps(src, ensure_ascii=False, indent=2)
        out = self._ask(TRANSLATE_SYSTEM, prompt, FIELDS, effort="low")
        return {k: (out[k] if src[k].strip() else "") for k in FIELDS}
