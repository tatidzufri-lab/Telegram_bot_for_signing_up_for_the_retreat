import asyncio
import json
import logging
import re

import httpx

from core import AssistantTurn, Settings, RetreatTicket
from core.schemas import DialogueMessage
from services.assistant.prompts import ASSISTANT_RESPONSE_SCHEMA, RETREAT_ASSISTANT_PROMPT

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


class OpenAIRetreatAssistant:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.openai_base_url,
            timeout=httpx.Timeout(45.0, connect=12.0),
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate_turn(
        self,
        current_ticket: RetreatTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
    ) -> AssistantTurn:
        payload = {
            "model": self._settings.openai_model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": RETREAT_ASSISTANT_PROMPT},
                {
                    "role": "user",
                    "content": self._build_user_prompt(
                        current_ticket=current_ticket,
                        user_message=user_message,
                        is_new_session=is_new_session,
                        conversation_history=conversation_history,
                        last_assistant_message=last_assistant_message,
                        telegram_first_name=telegram_first_name,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": ASSISTANT_RESPONSE_SCHEMA,
            },
        }

        try:
            response = await self._post_with_retries(payload)
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return AssistantTurn.model_validate(json.loads(content))
        except Exception:
            logger.exception("Falling back to local retreat turn generation")
            return self._build_fallback_turn(
                current_ticket=current_ticket,
                user_message=user_message,
                is_new_session=is_new_session,
                conversation_history=conversation_history,
                last_assistant_message=last_assistant_message,
                telegram_first_name=telegram_first_name,
            )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post_with_retries(self, payload: dict) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(1, 4):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_STATUS_CODES or attempt == 3:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == 3:
                    break

            await asyncio.sleep(0.75 * attempt)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _build_user_prompt(
        current_ticket: RetreatTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
    ) -> str:
        ticket_json = json.dumps(current_ticket.model_dump(), ensure_ascii=False, indent=2)
        history_json = json.dumps(
            [message.model_dump() for message in conversation_history],
            ensure_ascii=False,
            indent=2,
        )
        first_name = telegram_first_name or "null"
        last_bot_message = last_assistant_message or "null"

        return (
            f"is_new_session: {str(is_new_session).lower()}\n"
            f"telegram_first_name: {first_name}\n"
            f"current_ticket:\n{ticket_json}\n\n"
            f"conversation_history:\n{history_json}\n\n"
            f"last_assistant_message:\n{last_bot_message}\n\n"
            f"latest_user_message:\n{user_message}"
        )

    def _build_fallback_turn(
        self,
        current_ticket: RetreatTicket,
        user_message: str,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        last_assistant_message: str | None,
        telegram_first_name: str | None,
    ) -> AssistantTurn:
        message = self._normalize_text(user_message)
        message_lower = message.lower()
        extracted = RetreatTicket()
        requested_field = self._detect_requested_field(last_assistant_message)

        if self._is_repeat_question_request(message_lower):
            repeated = last_assistant_message or "Мы ещё не дошли до следующего вопроса."
            return AssistantTurn(
                reply=f"Мой последний вопрос был таким: {repeated}",
                extracted_ticket=extracted,
                ready_to_submit=current_ticket.is_complete(),
            )

        if not current_ticket.name and self._looks_like_name(message):
            extracted.name = message

        if not current_ticket.contact:
            contact = self._extract_contact(message)
            if contact:
                extracted.contact = contact

        if requested_field == "name" and not extracted.name and self._looks_like_name(message):
            extracted.name = message
        elif requested_field == "contact" and not extracted.contact:
            extracted.contact = self._extract_contact(message)
        elif requested_field == "request":
            extracted.request = self._extract_request(message, current_ticket)
        elif requested_field == "practice_experience":
            extracted.practice_experience = self._extract_practice_experience(message_lower)
        elif requested_field == "participation_format":
            extracted.participation_format = self._extract_participation_format(message_lower)
        elif requested_field == "retreat_dates":
            extracted.retreat_dates = message
        elif requested_field == "referral_source":
            extracted.referral_source = self._extract_referral_source(message_lower) or message

        if not extracted.request and not current_ticket.request and not self._looks_like_name(message):
            extracted.request = self._extract_request(message, current_ticket)

        if not extracted.practice_experience and not current_ticket.practice_experience:
            extracted.practice_experience = self._extract_practice_experience(message_lower)

        if not extracted.participation_format and not current_ticket.participation_format:
            extracted.participation_format = self._extract_participation_format(message_lower)

        if not extracted.referral_source and not current_ticket.referral_source:
            src = self._extract_referral_source(message_lower)
            if src:
                extracted.referral_source = src

        merged_ticket = current_ticket.model_copy(deep=True)
        merged_ticket.merge(extracted)

        reply = self._build_fallback_reply(
            merged_ticket=merged_ticket,
            extracted=extracted,
            is_new_session=is_new_session,
            conversation_history=conversation_history,
            telegram_first_name=telegram_first_name,
        )

        return AssistantTurn(
            reply=reply,
            extracted_ticket=extracted,
            ready_to_submit=merged_ticket.is_complete(),
        )

    def _build_fallback_reply(
        self,
        merged_ticket: RetreatTicket,
        extracted: RetreatTicket,
        is_new_session: bool,
        conversation_history: list[DialogueMessage],
        telegram_first_name: str | None,
    ) -> str:
        if not conversation_history and is_new_session and not extracted.name and not merged_ticket.name:
            return (
                "Привет! Я рада, что ты здесь 🌿 "
                "Меня зовут Лея — я помогу тебе узнать больше о ретрите «Познай себя» "
                "и подобрать подходящий формат. Как тебя зовут?"
            )

        if not merged_ticket.name:
            return "Подскажи, как тебя зовут?"

        name = merged_ticket.name or telegram_first_name or ""

        if not merged_ticket.request:
            prefix = f"{name}, " if name else ""
            return (
                f"Очень приятно, {name}! ✨ "
                f"{prefix}расскажи — что сейчас происходит в твоей жизни? "
                "Что привело тебя к ретриту?"
            ) if name else "Расскажи, что привело тебя к ретриту?"

        if not merged_ticket.practice_experience:
            return (
                "Спасибо, что поделилась 🌸 "
                "Скажи, был ли у тебя опыт медитаций, йоги или телесных практик? "
                "Варианты: есть опыт / немного, я начинающая / нет, всё впервые."
            )

        if not merged_ticket.participation_format:
            return (
                f"{name}, у нас три формата участия — посмотри, какой откликается:\n"
                "🌱 Базовый — 25 000 ₽\n"
                "🌿 Стандарт — 50 000 ₽\n"
                "✨ VIP — 75 000 ₽\n\n"
                "Какой тебе ближе?"
            )

        if not merged_ticket.retreat_dates:
            return "Какой заезд тебе подходит? Напиши удобные даты или период."

        if not merged_ticket.contact:
            return "Как лучше с тобой связаться? Напиши номер телефона или Telegram-username."

        if not merged_ticket.referral_source:
            return (
                "Откуда ты узнала о ретрите? "
                "Например: Instagram, Telegram-канал, рекомендация подруги или что-то другое."
            )

        return "Спасибо! Проверяю, всё ли записала 🌿"

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @staticmethod
    def _is_repeat_question_request(message_lower: str) -> bool:
        triggers = [
            "какой был прошлый вопрос",
            "какой был предыдущий вопрос",
            "повтори вопрос",
            "повтори последний вопрос",
            "что ты спрашивала",
            "что ты спросила",
        ]
        return any(trigger in message_lower for trigger in triggers)

    @staticmethod
    def _detect_requested_field(last_assistant_message: str | None) -> str | None:
        if not last_assistant_message:
            return None

        msg = last_assistant_message.lower()
        if any(phrase in msg for phrase in ["как тебя зовут", "как к тебе обращаться", "твоё имя"]):
            return "name"
        if any(phrase in msg for phrase in ["что привело", "что сейчас происходит", "расскажи"]):
            return "request"
        if any(phrase in msg for phrase in ["опыт медитаций", "опыт йоги", "телесных практик", "опыт практик"]):
            return "practice_experience"
        if any(phrase in msg for phrase in ["формат участия", "базовый", "стандарт", "vip", "какой тебе ближе"]):
            return "participation_format"
        if any(phrase in msg for phrase in ["заезд", "даты", "период"]):
            return "retreat_dates"
        if any(phrase in msg for phrase in ["связаться", "телефон", "username", "контакт"]):
            return "contact"
        if any(phrase in msg for phrase in ["откуда", "узнала о ретрите"]):
            return "referral_source"
        return None

    @staticmethod
    def _looks_like_name(message: str) -> bool:
        lowered = message.lower()
        blockers = [
            "ретрит", "медитац", "йог", "практик", "базов", "стандарт",
            "vip", "вип", "instagram", "telegram", "подруг", "рекоменд",
            "опыт", "начинающ", "впервые", "немного",
        ]
        if any(b in lowered for b in blockers):
            return False
        if any(char.isdigit() for char in message):
            return False
        words = [w for w in re.split(r"\s+", message) if w]
        return 1 <= len(words) <= 3

    @staticmethod
    def _extract_contact(message: str) -> str | None:
        if message.startswith("@") and len(message) > 1:
            return message
        compact = re.sub(r"[^\d+]", "", message)
        digits = re.sub(r"\D", "", compact)
        if len(digits) >= 10:
            return compact
        return None

    @staticmethod
    def _extract_practice_experience(message_lower: str) -> str | None:
        if any(token in message_lower for token in ["есть опыт", "да, есть", "давно практикую", "занимаюсь"]):
            return "есть опыт"
        if any(token in message_lower for token in ["немного", "начинающ", "чуть-чуть", "пробовала"]):
            return "немного"
        if any(token in message_lower for token in ["нет опыта", "нет,", "впервые", "не было", "не пробовала", "первый раз"]):
            return "нет опыта"
        return None

    @staticmethod
    def _extract_participation_format(message_lower: str) -> str | None:
        if any(token in message_lower for token in ["vip", "вип", "75"]):
            return "VIP"
        if any(token in message_lower for token in ["стандарт", "50"]):
            return "Стандарт"
        if any(token in message_lower for token in ["базов", "25"]):
            return "Базовый"
        return None

    @staticmethod
    def _extract_referral_source(message_lower: str) -> str | None:
        if "instagram" in message_lower or "инстаграм" in message_lower:
            return "Instagram"
        if "telegram" in message_lower or "телеграм" in message_lower:
            return "Telegram-канал"
        if any(token in message_lower for token in ["подруг", "рекоменд", "знакомая", "посоветовал"]):
            return "Рекомендация"
        return None

    def _extract_request(self, message: str, current_ticket: RetreatTicket) -> str | None:
        cleaned = self._normalize_text(message)
        if not cleaned or len(cleaned) < 10:
            return None
        if self._looks_like_name(cleaned):
            return None
        if current_ticket.request:
            return None
        return cleaned
