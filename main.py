import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Load .env from project dir
load_dotenv(Path(__file__).parent / ".env")

from config import config
from game.engine import wordlist
from handlers.common import register_common_handlers
from handlers.admin import register_admin_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("wordgame")


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set! Create .env with BOT_TOKEN=...")
        sys.exit(1)

    # Preload wordlists
    wordlist.load()
    logger.info("Wordlists loaded")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    register_common_handlers(dp)
    register_admin_handlers(dp)

    me = await bot.get_me()
    logger.info(f"Starting @{me.username} (id={me.id})")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
