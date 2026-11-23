import asyncio
import json
import logging
import re

import httpx

from core import AssistantTurn, Settings, RetreatTicket
from core.i18n import Lang
from core.schemas import DialogueMessage
from services.assistant.fallback import FALLBACK
from services.assistant.prompts import ASSISTANT_RESPONSE_SCHEMA, PROMPTS

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
        lang: Lang = "ru",
    ) -> AssistantTurn:
        payload = {
            "model": self._settings.openai_model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": PROMPTS[lang]},
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
                lang=lang,
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
        lang: Lang = "ru",
    ) -> AssistantTurn:
        """Локальный сценарий без модели: по словам в сообщении и последнем вопросе."""
        fb = FALLBACK[lang]
        message = self._normalize_text(user_message)
        message_lower = message.lower()
        extracted = RetreatTicket()
        requested_field = self._detect_requested_field(last_assistant_message, lang)

        if any(trigger in message_lower for trigger in fb["repeat_triggers"]):
            repeated = last_assistant_message or fb["no_question_yet"]
            return AssistantTurn(
                reply=fb["last_question"].format(q=repeated),
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
            extracted.referral_source = self._extract_referral_source(message_lower, lang) or message

        if not extracted.request and not current_ticket.request and not self._looks_like_name(message):
            extracted.request = self._extract_request(message, current_ticket)

        if not extracted.practice_experience and not current_ticket.practice_experience:
            extracted.practice_experience = self._extract_practice_experience(message_lower)

        if not extracted.participation_format and not current_ticket.participation_format:
            extracted.participation_format = self._extract_participation_format(message_lower)

        if not extracted.referral_source and not current_ticket.referral_source:
            src = self._extract_referral_source(message_lower, lang)
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
            lang=lang,
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
        lang: Lang = "ru",
    ) -> str:
        fb = FALLBACK[lang]
        if not conversation_history and is_new_session and not extracted.name and not merged_ticket.name:
            return fb["greeting"]

        if not merged_ticket.name:
            return fb["ask_name"]

        name = merged_ticket.name or telegram_first_name or ""

        if not merged_ticket.request:
            return fb["ask_request_named"].format(name=name) if name else fb["ask_request"]

        if not merged_ticket.practice_experience:
            return fb["ask_experience"]

        if not merged_ticket.participation_format:
            return fb["ask_format"].format(name=name)

        if not merged_ticket.retreat_dates:
            return fb["ask_dates"]

        if not merged_ticket.contact:
            return fb["ask_contact"]

        if not merged_ticket.referral_source:
            return fb["ask_source"]

        return fb["checking"]

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @staticmethod
    def _detect_requested_field(last_assistant_message: str | None, lang: Lang = "ru") -> str | None:
        if not last_assistant_message:
            return None
        msg = last_assistant_message.lower()
        # Вопрос мог быть задан на другом языке, если участница переключила язык.
        for markers in (FALLBACK[lang]["field_markers"], *(FALLBACK[o]["field_markers"] for o in FALLBACK if o != lang)):
            for field, phrases in markers:
                if any(phrase in msg for phrase in phrases):
                    return field
        return None

    @staticmethod
    def _looks_like_name(message: str) -> bool:
        lowered = message.lower()
        blockers = [b for fb in FALLBACK.values() for b in fb["name_blockers"]]
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
        # Ключевые слова обоих языков: ответить можно на любом.
        for code in ("experienced", "some", "none"):
            if any(token in message_lower for fb in FALLBACK.values() for token in fb["experience_tokens"][code]):
                return code
        return None

    @staticmethod
    def _extract_participation_format(message_lower: str) -> str | None:
        for code in ("vip", "standard", "basic"):
            if any(token in message_lower for fb in FALLBACK.values() for token in fb["format_tokens"][code]):
                return code
        return None

    @staticmethod
    def _extract_referral_source(message_lower: str, lang: Lang = "ru") -> str | None:
        labels = FALLBACK[lang]["source_labels"]
        if "instagram" in message_lower or "инстаграм" in message_lower:
            return "Instagram"
        if "telegram" in message_lower or "телеграм" in message_lower:
            return labels["telegram"]
        if any(token in message_lower for fb in FALLBACK.values() for token in fb["recommendation_tokens"]):
            return labels["recommendation"]
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
