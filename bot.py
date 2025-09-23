import sys
from os import getenv
from dotenv import load_dotenv
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.exceptions import TelegramNetworkError
from aiohttp import web, ClientConnectorError, ClientConnectorDNSError
import asyncio

from handlers import router

# Конфигурация логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Обязательно для Render
        logging.FileHandler("bot.log", encoding="utf-8")
    ],
    force=True  # Перезаписывает существующие handlers
)

# Глобальные переменные
load_dotenv()
BOT_TOKEN = getenv("BOT_TOKEN")
WEBHOOK_HOST = getenv("WEBHOOK_HOST")  # Например, https://your-bot-domain.com
WEBHOOK_PATH = "/webhook"  # Путь для Telegram
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"  # Локальный хост для веб-сервера
WEBAPP_PORT = int(getenv("PORT", 3000))  # Порт от хостинга или 3000 по умолчанию

# Исключения для повторных попыток
RETRY_EXC = (
    TelegramNetworkError,
    ClientConnectorError,
    ClientConnectorDNSError,
    asyncio.TimeoutError,
    OSError
)

async def handle_webhook(request, bot, dp):
    print("=== ВХОДЯЩИЙ WEBHOOK ===")
    try:
        data = await request.json()
        print(f"Получено обновление: {data.get('message', {}).get('text', 'нет текста')}")
        update = Update(**data)
        await dp.feed_update(bot=bot, update=update)
        print("✅ Обновление обработано")
        return web.Response(status=200)
    except Exception as e:
        print(f"❌ Ошибка в handle_webhook: {e}")
        logging.error(f"Ошибка webhook: {e}")
        return web.Response(status=500)

async def on_startup(bot, _):
    """Установка webhook при запуске"""
    print("=== ON_STARTUP ===")
    print(f"WEBHOOK_URL: {WEBHOOK_URL}")
    try:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook установлен на {WEBHOOK_URL}")
        print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")
        logging.exception(f"Ошибка webhook: {e}")
        raise

async def on_shutdown(bot, _):
    """Удаление webhook при остановке"""
    try:
        await bot.delete_webhook()
        logging.info("Webhook удалён")
        print("Бот остановлен")
    except Exception as e:
        logging.error(f"Ошибка при удалении webhook: {e}")

async def main():
    print("=== ЗАПУСК BOT ===")  # Для проверки в логах Render
    bot = Bot(token=BOT_TOKEN)
    print(f"BOT_TOKEN загружен: {'да' if BOT_TOKEN else 'НЕТ! Ошибка!'}")
    dp = Dispatcher()
    dp.include_router(router)
    print("Dispatcher и router подключены")

    # Настройка веб-сервера
    app = web.Application()
    # Передаём bot и dp в handle_webhook через lambda
    app.router.add_post(WEBHOOK_PATH, lambda request: handle_webhook(request, bot, dp))
    app.on_startup.append(lambda _: on_startup(bot, _))
    app.on_shutdown.append(lambda _: on_shutdown(bot, _))

    logging.info("Starting bot in webhook mode...")
    print("Бот запускается...")

    # Запуск веб-сервера
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
        await site.start()
        logging.info(f"Веб-сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")
        print(f"Веб-сервер запущен на порт {WEBAPP_PORT}")
        # Держим сервер активным
        await asyncio.Event().wait()
    except RETRY_EXC as e:
        logging.warning(f"Ошибка веб-сервера: {e}. Повтор через 5с")
        await asyncio.sleep(5)
        raise  # Перезапуск хостингом
    except Exception as e:
        logging.exception(f"Фатальная ошибка: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен.")
    except Exception as e:
        logging.exception(f"Критическая ошибка: {e}")
        print("Бот остановлен из-за ошибки.")