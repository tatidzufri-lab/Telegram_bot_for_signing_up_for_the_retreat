from aiogram import Bot

from core import Settings, RetreatSession
from core.i18n import EXPERIENCE_LABELS, FORMAT_LABELS, label

CARD = {
    "ru": {
        "title": "=== НОВАЯ ЗАЯВКА НА РЕТРИТ ===", "name": "Имя", "request": "Запрос",
        "experience": "Опыт практик", "format": "Формат участия", "dates": "Даты / поток",
        "contact": "Контакт", "source": "Откуда узнала", "end": "=== КОНЕЦ ===",
    },
    "en": {
        "title": "=== NEW RETREAT REQUEST · EN ===", "name": "Name", "request": "Request",
        "experience": "Practice experience", "format": "Format", "dates": "Dates / session",
        "contact": "Contact", "source": "Heard about us from", "end": "=== END ===",
    },
}


class OperatorNotifier:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send_ticket(self, session: RetreatSession) -> None:
        ticket = session.ticket
        lang = session.lang
        c = CARD[lang]
        lines = [
            c["title"],
            "",
            f"{c['name']}: {ticket.name}",
            "",
            f"{c['request']}:",
            f"{ticket.request}",
            "",
            f"{c['experience']}: {label(EXPERIENCE_LABELS, ticket.practice_experience, lang)}",
            f"{c['format']}: {label(FORMAT_LABELS, ticket.participation_format, lang)}",
            f"{c['dates']}: {ticket.retreat_dates}",
            "",
            f"{c['contact']}: {ticket.contact}",
            f"{c['source']}: {ticket.referral_source}",
            "",
            f"Telegram user id: {session.user_id}",
            f"Telegram username: @{session.telegram_username}" if session.telegram_username else "Telegram username: -",
            "",
            c["end"],
        ]
        await self._bot.send_message(self._settings.operator_chat_id, "\n".join(lines))
