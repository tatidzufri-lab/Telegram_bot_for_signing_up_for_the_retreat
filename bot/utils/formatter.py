from core import RetreatTicket


def format_collected_ticket(ticket: RetreatTicket) -> str:
    lines = [
        f"Имя: {ticket.name or '-'}",
        f"Запрос: {ticket.request or '-'}",
        f"Опыт практик: {ticket.practice_experience or '-'}",
        f"Формат: {ticket.participation_format or '-'}",
        f"Даты: {ticket.retreat_dates or '-'}",
        f"Контакт: {ticket.contact or '-'}",
        f"Откуда узнала: {ticket.referral_source or '-'}",
    ]
    return "\n".join(lines)
