from aiogram import Bot

from core import Settings, RetreatSession


class OperatorNotifier:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self._bot = bot
        self._settings = settings

    async def send_ticket(self, session: RetreatSession) -> None:
        ticket = session.ticket
        lines = [
            "=== НОВАЯ ЗАЯВКА НА РЕТРИТ ===",
            "",
            f"Имя: {ticket.name}",
            "",
            "Запрос:",
            f"{ticket.request}",
            "",
            f"Опыт практик: {ticket.practice_experience}",
            f"Формат участия: {ticket.participation_format}",
            f"Даты / поток: {ticket.retreat_dates}",
            "",
            f"Контакт: {ticket.contact}",
            f"Откуда узнала: {ticket.referral_source}",
            "",
            f"Telegram user id: {session.user_id}",
            f"Telegram username: @{session.telegram_username}" if session.telegram_username else "Telegram username: -",
            "",
            "=== КОНЕЦ ===",
        ]
        await self._bot.send_message(self._settings.operator_chat_id, "\n".join(lines))
