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


REPLY_SYSTEM = """Ты помогаешь продавцу на маркетплейсе FunPay отвечать покупателям и на отзывы.
Правила FunPay: никаких контактов и ссылок вне FunPay, не просить покупателя писать в другие мессенджеры,
не обещать того, чего продавец не говорил. Тон — дружелюбный и профессиональный, без канцелярита.
Верни только текст сообщения в поле text, без кавычек и пояснений."""


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

    def reply_chat(self, messages: list[dict], hint: str = "") -> dict:
        """Черновик ответа покупателю по истории чата (последние сообщения)."""
        lines = []
        for m in messages:
            who = "Система FunPay" if m.get("system") else ("Продавец (я)" if m.get("mine") else f"Покупатель {m.get('name') or ''}".strip())
            text = (m.get("text") or ("[картинка]" if m.get("image") else "")).strip()
            if text:
                lines.append(f"{who}: {text}")
        if not lines:
            raise AIError("В чате нет сообщений, на которые можно ответить.")
        prompt = ("Переписка в чате FunPay (старые сверху):\n" + "\n".join(lines[-30:]) +
                  "\n\nНапиши следующее сообщение продавца покупателю: по делу, вежливо, коротко, на языке покупателя."
                  + (f"\nЧто хочет сказать продавец: {hint.strip()}" if hint and hint.strip() else
                     "\nЕсли не хватает фактов (наличие, сроки), не выдумывай — уточни у покупателя или ответь общо."))
        return self._ask(REPLY_SYSTEM, prompt, ("text",), effort="low")

    def reply_review(self, review: str, rating: int | None, lot_title: str, hint: str = "") -> dict:
        if not (review or "").strip():
            raise AIError("У заказа нет отзыва.")
        prompt = (f"Лот: {lot_title or '—'}\nОценка покупателя: {rating or '—'} из 5\nОтзыв: {review.strip()}\n\n"
                  "Напиши публичный ответ продавца на этот отзыв: 1–3 предложения, вежливо, без оправданий и споров; "
                  "на благодарность — поблагодари, на жалобу — спокойно и по делу."
                  + (f"\nЧто хочет сказать продавец: {hint.strip()}" if hint and hint.strip() else ""))
        return self._ask(REPLY_SYSTEM, prompt, ("text",), effort="low")

    def translate(self, fields: dict) -> dict:
        src = {k: (fields or {}).get(k, "") for k in FIELDS}
        if not any(v.strip() for v in src.values()):
            raise AIError("Нечего переводить: русские поля пустые.")
        prompt = "Translate each field to English:\n\n" + json.dumps(src, ensure_ascii=False, indent=2)
        out = self._ask(TRANSLATE_SYSTEM, prompt, FIELDS, effort="low")
        return {k: (out[k] if src[k].strip() else "") for k in FIELDS}
