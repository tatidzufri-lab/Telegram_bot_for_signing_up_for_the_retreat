import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from core import RetreatSession
from core.i18n import LANGS, Lang, lang_from_telegram, t
from services import RetreatWorkflowService
from services.storage import InMemorySessionRepository

logger = logging.getLogger(__name__)
router = Router()

LANGUAGE_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    ]]
)


def _session_for(message: Message, session_repository: InMemorySessionRepository) -> RetreatSession:
    user = message.from_user
    known = session_repository.exists(user.id)
    session = session_repository.get_or_create(
        user_id=user.id,
        chat_id=message.chat.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
    )
    if not known:
        session.lang = lang_from_telegram(user.language_code)
    return session


def _guess_lang(message: Message) -> Lang:
    return lang_from_telegram(message.from_user.language_code if message.from_user else None)


@router.message(CommandStart())
async def handle_start(
    message: Message,
    command: CommandObject,
    session_repository: InMemorySessionRepository,
) -> None:
    user = message.from_user
    if user is None:
        await message.answer(t("no_user", "ru"))
        return

    session = _session_for(message, session_repository)
    # t.me/<бот>?start=en — ссылка с английской страницы сайта
    if command.args in LANGS:
        session.lang = command.args
    session.reset()
    session.started = True

    if user.username:
        session.ticket.contact = f"@{user.username}"

    greeting = t("start", session.lang)
    session.add_assistant_message(greeting)
    await message.answer(greeting)


@router.message(Command("reset"))
async def handle_reset(
    message: Message,
    session_repository: InMemorySessionRepository,
) -> None:
    user = message.from_user
    if user is None:
        await message.answer(t("no_user", _guess_lang(message)))
        return

    session = _session_for(message, session_repository)
    session.reset()
    session.started = True
    if user.username:
        session.ticket.contact = f"@{user.username}"

    text = t("reset", session.lang)
    session.add_assistant_message(text)
    await message.answer(text)


@router.message(Command("language"))
async def handle_language(message: Message, session_repository: InMemorySessionRepository) -> None:
    if message.from_user is None:
        return
    session = _session_for(message, session_repository)
    await message.answer(t("choose_language", session.lang), reply_markup=LANGUAGE_KEYBOARD)


@router.message(Command("en", "ru"))
async def handle_language_shortcut(
    message: Message,
    command: CommandObject,
    session_repository: InMemorySessionRepository,
) -> None:
    if message.from_user is None:
        return
    session = _session_for(message, session_repository)
    session.lang = command.command
    await message.answer(t("language_set", session.lang))


@router.callback_query(F.data.startswith("lang:"))
async def handle_language_choice(
    callback: CallbackQuery,
    session_repository: InMemorySessionRepository,
) -> None:
    lang = callback.data.split(":", 1)[1]
    if lang not in LANGS or callback.message is None:
        await callback.answer()
        return
    user = callback.from_user
    session = session_repository.get_or_create(
        user_id=user.id,
        chat_id=callback.message.chat.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
    )
    session.lang = lang
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t("language_set", lang))


@router.message(F.text)
async def handle_text_message(
    message: Message,
    session_repository: InMemorySessionRepository,
    workflow: RetreatWorkflowService,
) -> None:
    user = message.from_user
    if user is None or not message.text:
        await message.answer(t("no_user", _guess_lang(message)))
        return

    session = _session_for(message, session_repository)

    try:
        reply = await workflow.process_message(session, message.text)
        await message.answer(reply)
    except Exception:
        logger.exception("Failed to process incoming retreat message")
        await message.answer(t("generic_error", session.lang))


@router.message()
async def handle_unsupported_message(
    message: Message,
    session_repository: InMemorySessionRepository,
) -> None:
    if message.from_user is None:
        return
    session = _session_for(message, session_repository)
    await message.answer(t("unsupported", session.lang))
