import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from bot.handlers import router
from core import get_settings, setup_logging
from core.i18n import COMMANDS, DESCRIPTION_EN, DESCRIPTION_RU, SHORT_DESCRIPTION_EN, SHORT_DESCRIPTION_RU
from services import RetreatWorkflowService
from services.assistant import OpenAIRetreatAssistant
from services.storage import InMemorySessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)


async def setup_bot_profile(bot: Bot) -> None:
    """Меню команд и описание бота на двух языках (русское — по умолчанию)."""
    try:
        for lang, language_code in (("ru", None), ("ru", "ru"), ("ru", "uk"), ("en", "en")):
            commands = [BotCommand(command=c, description=d) for c, d in COMMANDS[lang]]
            await bot.set_my_commands(commands, language_code=language_code)
        await bot.set_my_description(DESCRIPTION_RU)
        await bot.set_my_short_description(SHORT_DESCRIPTION_RU)
        await bot.set_my_description(DESCRIPTION_EN, language_code="en")
        await bot.set_my_short_description(SHORT_DESCRIPTION_EN, language_code="en")
    except Exception:
        logger.exception("Could not set bot commands/description")


async def run_bot() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    bot = Bot(token=settings.telegram_bot_token, default=DefaultBotProperties())
    session_repository = InMemorySessionRepository()
    assistant = OpenAIRetreatAssistant(settings)
    notifier = OperatorNotifier(bot, settings)
    workflow = RetreatWorkflowService(assistant=assistant, notifier=notifier)

    dp = Dispatcher()
    dp.include_router(router)
    dp["session_repository"] = session_repository
    dp["workflow"] = workflow

    await setup_bot_profile(bot)
    logger.info("Starting retreat intake bot")
    try:
        await dp.start_polling(bot)
    finally:
        await workflow.close()
        await bot.session.close()
