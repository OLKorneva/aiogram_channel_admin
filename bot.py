import sys
from os import getenv
from dotenv import load_dotenv
import logging
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiohttp import ClientConnectorError, ClientConnectorDNSError
import asyncio

from handlers import router

# Конфигурация логирования
# logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="bot.log",
    encoding="utf-8"
)

# Глобальные переменные
load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")

# Исключения для повторных попыток
RETRY_EXC = (
    TelegramNetworkError,
    ClientConnectorError,
    ClientConnectorDNSError,
    asyncio.TimeoutError,
    OSError
)

async def run_polling_forever(bot: Bot, dp: Dispatcher):
    backoff = 2
    max_backoff = 30
    while True:
        try:
            await dp.start_polling(bot)
            # Корректный выход
            logging.info("Bot stopped gracefully")
            break
        except RETRY_EXC as e:
            logging.warning(f"Network error: {e}. Retry in {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
        except Exception:
            logging.exception("Fatal error. Stopping bot.")
            break

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    logging.info("Starting bot...")
    print("Бот запущен")
    await run_polling_forever(bot, dp)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
