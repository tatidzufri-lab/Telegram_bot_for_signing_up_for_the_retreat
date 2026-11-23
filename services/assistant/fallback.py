"""Тексты и ключевые слова локального сценария (когда OpenAI недоступен).

Распознавание ответов работает на словах обоих языков: участница может
ответить по-русски в английском диалоге и наоборот.
"""

from core.i18n import TEXTS

FALLBACK: dict = {
    "ru": {
        "greeting": TEXTS["start"]["ru"],
        "ask_name": "Подскажи, как тебя зовут?",
        "ask_request_named": (
            "Очень приятно, {name}! ✨ "
            "{name}, расскажи — что сейчас происходит в твоей жизни? "
            "Что привело тебя к ретриту?"
        ),
        "ask_request": "Расскажи, что привело тебя к ретриту?",
        "ask_experience": (
            "Спасибо, что поделилась 🌸 "
            "Скажи, был ли у тебя опыт медитаций, йоги или телесных практик? "
            "Варианты: есть опыт / немного, я начинающая / нет, всё впервые."
        ),
        "ask_format": (
            "{name}, у нас три формата участия — посмотри, какой откликается:\n"
            "🌱 Базовый — 25 000 ₽\n"
            "🌿 Стандарт — 50 000 ₽\n"
            "✨ VIP — 75 000 ₽\n\n"
            "Какой тебе ближе?"
        ),
        "ask_dates": "Какой заезд тебе подходит? Напиши удобные даты или период.",
        "ask_contact": "Как лучше с тобой связаться? Напиши номер телефона или Telegram-username.",
        "ask_source": (
            "Откуда ты узнала о ретрите? "
            "Например: Instagram, Telegram-канал, рекомендация подруги или что-то другое."
        ),
        "checking": "Спасибо! Проверяю, всё ли записала 🌿",
        "no_question_yet": "Мы ещё не дошли до следующего вопроса.",
        "last_question": "Мой последний вопрос был таким: {q}",
        "repeat_triggers": [
            "какой был прошлый вопрос",
            "какой был предыдущий вопрос",
            "повтори вопрос",
            "повтори последний вопрос",
            "что ты спрашивала",
            "что ты спросила",
        ],
        "field_markers": [
            ("name", ["как тебя зовут", "как к тебе обращаться", "твоё имя"]),
            ("request", ["что привело", "что сейчас происходит", "расскажи"]),
            ("practice_experience", ["опыт медитаций", "опыт йоги", "телесных практик", "опыт практик"]),
            ("participation_format", ["формат участия", "базовый", "стандарт", "vip", "какой тебе ближе"]),
            ("retreat_dates", ["заезд", "даты", "период"]),
            ("contact", ["связаться", "телефон", "username", "контакт"]),
            ("referral_source", ["откуда", "узнала о ретрите"]),
        ],
        "name_blockers": [
            "ретрит", "медитац", "йог", "практик", "базов", "стандарт",
            "vip", "вип", "instagram", "telegram", "подруг", "рекоменд",
            "опыт", "начинающ", "впервые", "немного",
        ],
        "experience_tokens": {
            "experienced": ["есть опыт", "да, есть", "давно практикую", "занимаюсь"],
            "none": ["нет опыта", "нет,", "впервые", "не было", "не пробовала", "первый раз"],
            "some": ["немного", "начинающ", "чуть-чуть", "пробовала"],
        },
        "format_tokens": {
            "vip": ["vip", "вип", "75"],
            "standard": ["стандарт", "50"],
            "basic": ["базов", "25"],
        },
        "recommendation_tokens": ["подруг", "рекоменд", "знакомая", "посоветовал"],
        "source_labels": {"telegram": "Telegram-канал", "recommendation": "Рекомендация"},
    },
    "en": {
        "greeting": TEXTS["start"]["en"],
        "ask_name": "What's your name?",
        "ask_request_named": (
            "Lovely to meet you, {name}! ✨ "
            "Tell me, what's happening in your life right now? "
            "What brings you to the retreat?"
        ),
        "ask_request": "Tell me, what brings you to the retreat?",
        "ask_experience": (
            "Thank you for sharing 🌸 "
            "Have you had any experience with meditation, yoga or body practices? "
            "Options: yes, I have experience / a little, I'm a beginner / no, it's all new to me."
        ),
        "ask_format": (
            "{name}, we have three formats. See which one resonates:\n"
            "🌱 Basic: $390 (online course)\n"
            "🌿 Standard: $1,490 (online course + 5 days in the Dolomites)\n"
            "✨ VIP: $2,290 (Standard + single room and personal sessions)\n\n"
            "Which one feels right?"
        ),
        "ask_dates": "Which session works for you? Send the dates or period that suit you.",
        "ask_contact": "How can the curator reach you? Send your phone number or Telegram username.",
        "ask_source": (
            "How did you hear about the retreat? "
            "For example: Instagram, a Telegram channel, a friend's recommendation or something else."
        ),
        "checking": "Thank you! Let me check I've got everything 🌿",
        "no_question_yet": "We haven't got to the next question yet.",
        "last_question": "My last question was: {q}",
        "repeat_triggers": [
            "what was your last question",
            "what was the last question",
            "what was the previous question",
            "repeat the question",
            "repeat your question",
            "what did you ask",
        ],
        "field_markers": [
            ("name", ["what's your name", "what is your name", "what should i call you"]),
            ("request", ["what brings you", "what's happening", "tell me"]),
            ("practice_experience", ["experience with meditation", "meditation, yoga", "body practices"]),
            ("participation_format", ["three formats", "basic", "standard", "vip", "which one feels"]),
            ("retreat_dates", ["which session", "dates", "period"]),
            ("contact", ["reach you", "phone", "username", "contact"]),
            ("referral_source", ["how did you hear", "hear about"]),
        ],
        "name_blockers": [
            "retreat", "meditat", "yoga", "practice", "basic", "standard",
            "friend", "recommend", "experience", "beginner", "never", "a little",
            "first time", "online",
        ],
        "experience_tokens": {
            "experienced": ["i have experience", "yes, i have", "experienced", "i practice", "been practicing", "practise regularly"],
            "none": ["no experience", "never", "first time", "all new", "no,"],
            "some": ["a little", "beginner", "a bit", "some experience", "tried"],
        },
        "format_tokens": {
            "vip": ["vip", "2290", "2,290", "summit"],
            "standard": ["standard", "1490", "1,490", "harmony"],
            "basic": ["basic", "390", "online only", "path to self"],
        },
        "recommendation_tokens": ["friend", "recommend", "word of mouth"],
        "source_labels": {"telegram": "Telegram channel", "recommendation": "Recommendation"},
    },
}
