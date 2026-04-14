import logging

from core import RetreatSession
from services.assistant import OpenAIRetreatAssistant
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)

FINAL_CLIENT_MESSAGE = (
    "Спасибо! 🌿 Куратор ретрита напишет тебе в течение 24 часов. "
    "До встречи на ретрите — я верю, что это путешествие изменит тебя ✨"
)


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
        history_before_turn = session.recent_history()
        is_new_session = not history_before_turn and not session.started

        turn = await self._assistant.generate_turn(
            current_ticket=session.ticket,
            user_message=message_text,
            is_new_session=is_new_session,
            conversation_history=history_before_turn,
            last_assistant_message=session.last_assistant_message,
            telegram_first_name=session.telegram_first_name,
        )

        session.add_user_message(message_text)
        session.ticket.merge(turn.extracted_ticket)
        session.started = True

        if session.ticket.is_complete() and turn.ready_to_submit:
            await self._notifier.send_ticket(session)
            session.submitted = True
            session.add_assistant_message(FINAL_CLIENT_MESSAGE)
            logger.info("Retreat ticket submitted for user_id=%s", session.user_id)
            return FINAL_CLIENT_MESSAGE

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
