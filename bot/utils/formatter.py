from core import RetreatTicket
from core.i18n import EXPERIENCE_LABELS, FORMAT_LABELS, label


def format_collected_ticket(ticket: RetreatTicket) -> str:
    lines = [
        f"Имя: {ticket.name or '-'}",
        f"Запрос: {ticket.request or '-'}",
        f"Опыт практик: {label(EXPERIENCE_LABELS, ticket.practice_experience, 'ru') or '-'}",
        f"Формат: {label(FORMAT_LABELS, ticket.participation_format, 'ru') or '-'}",
        f"Даты: {ticket.retreat_dates or '-'}",
        f"Контакт: {ticket.contact or '-'}",
        f"Откуда узнала: {ticket.referral_source or '-'}",
    ]
    return "\n".join(lines)
