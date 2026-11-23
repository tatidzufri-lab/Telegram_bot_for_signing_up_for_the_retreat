import logging

from core import RetreatSession
from core.i18n import lang_from_text, t
from services.assistant import OpenAIRetreatAssistant
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)


class RetreatWorkflowService:
    def __init__(
        self,
        assistant: OpenAIRetreatAssistant,
        notifier: OperatorNotifier,
    ) -> None:
        self._assistant = assistant
        self._notifier = notifier

    async def process_message(self, session: RetreatSession, message_text: str) -> str:
        if session.submitted:
            session.reset()

        self._prefill_contact_from_telegram(session)
        # Участница пишет на другом языке — Лея переходит на него.
        session.lang = lang_from_text(message_text) or session.lang
        history_before_turn = session.recent_history()
        is_new_session = not history_before_turn and not session.started

        turn = await self._assistant.generate_turn(
            current_ticket=session.ticket,
            user_message=message_text,
            is_new_session=is_new_session,
            conversation_history=history_before_turn,
            last_assistant_message=session.last_assistant_message,
            telegram_first_name=session.telegram_first_name,
            lang=session.lang,
        )

        session.add_user_message(message_text)
        session.ticket.merge(turn.extracted_ticket)
        session.started = True

        if session.ticket.is_complete() and turn.ready_to_submit:
            await self._notifier.send_ticket(session)
            session.submitted = True
            final = t("final", session.lang)
            session.add_assistant_message(final)
            logger.info("Retreat ticket submitted for user_id=%s lang=%s", session.user_id, session.lang)
            return final

        session.add_assistant_message(turn.reply)
        return turn.reply

    @staticmethod
    def _prefill_contact_from_telegram(session: RetreatSession) -> None:
        if session.ticket.contact:
            return
        if session.telegram_username:
            session.ticket.contact = f"@{session.telegram_username}"

    async def close(self) -> None:
        await self._assistant.close()
