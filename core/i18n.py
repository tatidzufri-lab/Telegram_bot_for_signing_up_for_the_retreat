"""Два языка бота: русский и английский.

Язык сессии выбирается так:
1. /start en или /start ru (ссылка t.me/<бот>?start=en с английской страницы сайта);
2. команды /language, /en, /ru;
3. язык интерфейса Telegram (ru, uk, be, kk → русский, остальные → английский);
4. по ходу диалога: кириллица в сообщении → русский, связная латиница → английский.
"""

from __future__ import annotations

import re
from typing import Literal

Lang = Literal["ru", "en"]
LANGS: tuple[Lang, ...] = ("ru", "en")

_RU_FAMILY = ("ru", "uk", "be", "kk")
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")
_LATIN_WORD = re.compile(r"[A-Za-z]{2,}")


def lang_from_telegram(language_code: str | None) -> Lang:
    if not language_code:
        return "ru"
    return "ru" if language_code.lower().startswith(_RU_FAMILY) else "en"


def lang_from_text(text: str) -> Lang | None:
    """Уверенно определяет язык сообщения или возвращает None.

    Короткие латинские ответы (имя, @username, «VIP») язык не меняют.
    """
    if _CYRILLIC.search(text):
        return "ru"
    if len(_LATIN_WORD.findall(text)) >= 3:
        return "en"
    return None


TEXTS: dict[str, dict[Lang, str]] = {
    "start": {
        "ru": (
            "Привет! Я рада, что ты здесь 🌿 "
            "Меня зовут Лея — я помогу тебе узнать больше о ретрите «Познай себя» "
            "и подобрать подходящий формат. Как тебя зовут?"
        ),
        "en": (
            "Hi! I'm so glad you're here 🌿 "
            "I'm Leya, and I'll help you learn more about the Know Yourself retreat "
            "and find the format that suits you. What's your name?"
        ),
    },
    "reset": {
        "ru": "Начнём сначала 🌿 Как тебя зовут?",
        "en": "Let's start over 🌿 What's your name?",
    },
    "generic_error": {
        "ru": "Прости, сейчас не получилось обработать сообщение. Попробуй ещё раз через пару минут 🌸",
        "en": "Sorry, I couldn't process that message just now. Please try again in a couple of minutes 🌸",
    },
    "unsupported": {
        "ru": "Напиши мне текстом, и я с радостью помогу 🌿",
        "en": "Please write to me in text, and I'll be happy to help 🌿",
    },
    "no_user": {
        "ru": "Не удалось определить пользователя. Попробуй ещё раз.",
        "en": "I couldn't identify you. Please try again.",
    },
    "choose_language": {
        "ru": "Выбери язык общения:",
        "en": "Choose the language:",
    },
    "language_set": {
        "ru": "Хорошо, дальше говорим по-русски 🌿",
        "en": "Great, let's continue in English 🌿",
    },
    "final": {
        "ru": (
            "Спасибо! 🌿 Куратор ретрита напишет тебе в течение 24 часов. "
            "До встречи на ретрите — я верю, что это путешествие изменит тебя ✨"
        ),
        "en": (
            "Thank you! 🌿 The retreat curator will message you within 24 hours. "
            "See you at the retreat. I believe this journey will change you ✨"
        ),
    },
}

COMMANDS: dict[Lang, list[tuple[str, str]]] = {
    "ru": [
        ("start", "Начать знакомство с Леей"),
        ("reset", "Начать заново"),
        ("language", "Сменить язык / Change language"),
    ],
    "en": [
        ("start", "Start a conversation with Leya"),
        ("reset", "Start over"),
        ("language", "Change language / Сменить язык"),
    ],
}

DESCRIPTION_EN = (
    "Hi! I'm Leya, the assistant of the Know Yourself retreat. "
    "I'll get to know you, help you pick a format and pass your request to the curator. "
    "Я говорю и по-русски: /language"
)
SHORT_DESCRIPTION_EN = "Leya, assistant of the Know Yourself retreat. Signs you up in a short chat."

# Значения полей заявки хранятся кодами, подписи зависят от языка.
EXPERIENCE_LABELS: dict[str, dict[Lang, str]] = {
    "experienced": {"ru": "есть опыт", "en": "experienced"},
    "some": {"ru": "немного", "en": "a little"},
    "none": {"ru": "нет опыта", "en": "no experience"},
}
FORMAT_LABELS: dict[str, dict[Lang, str]] = {
    "basic": {"ru": "Базовый", "en": "Basic"},
    "standard": {"ru": "Стандарт", "en": "Standard"},
    "vip": {"ru": "VIP", "en": "VIP"},
}


def t(key: str, lang: Lang) -> str:
    return TEXTS[key][lang]


def label(mapping: dict[str, dict[Lang, str]], code: str | None, lang: Lang) -> str | None:
    if code is None:
        return None
    return mapping.get(code, {}).get(lang, code)
