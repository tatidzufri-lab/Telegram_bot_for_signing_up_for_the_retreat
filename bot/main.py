import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.handlers import router
from core import get_settings, setup_logging
from services import RetreatWorkflowService
from services.assistant import OpenAIRetreatAssistant
from services.storage import InMemorySessionRepository
from services.telegram import OperatorNotifier

logger = logging.getLogger(__name__)


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

    logger.info("Starting retreat intake bot")
    try:
        await dp.start_polling(bot)
    finally:
        await workflow.close()
        await bot.session.close()
