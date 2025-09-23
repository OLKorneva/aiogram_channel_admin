from os import getenv
from dotenv import load_dotenv
from aiogram import Router, Bot, types
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.types import ChatMemberUpdated
from aiogram.filters import CommandStart
from utils import give_user_inf, event_message
import asyncio
import logging
from typing import Optional
from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError

router = Router()

# Глобальные переменные
load_dotenv()
ADMIN_ID = getenv("ADMIN_ID")
CHANNEL_ID = getenv("CHANNEL_ID")

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("👋 Теперь я смогу отправлять вам уведомления!")

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_joined(event: ChatMemberUpdated, bot: Bot):  # bot как dependency
    if event.chat.id == int(CHANNEL_ID):
        user = event.new_chat_member.user
        await send_message_to_admin(bot, user, event_message.get('add'))

@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_left(event: ChatMemberUpdated, bot: Bot):  # bot как dependency
    if event.chat.id == int(CHANNEL_ID):
        user = event.old_chat_member.user
        await send_message_to_admin(bot, user, event_message.get('left'))


# Исключения для повторных попыток
RETRY_EXC = (
    TelegramAPIError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError
)

async def send_message_to_admin(
        bot: Bot,
        user: types.User,
        event: str,
        max_retries: int = 3,
        initial_delay: float = 1.0
) -> Optional[types.Message]:
    """
    Отправляет сообщение админу с обработкой ошибок и повторными попытками

    Args:
        bot: Экземпляр бота
        user: Пользователь
        event: Событие
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка между попытками

    Returns:
        Message object если успешно, None если все попытки провалились
    """
    user_inf = await give_user_inf(user)
    admin_message = f'{event}\n{user_inf}'

    delay = initial_delay
    attempt = 0

    while attempt < max_retries:
        try:
            message = await bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logging.info(f"Сообщение админу отправлено успешно (попытка {attempt + 1})")
            return message

        except RETRY_EXC as e:
            attempt += 1
            if attempt >= max_retries:
                logging.error(
                    f"Не удалось отправить сообщение админу после {max_retries} попыток. "
                    f"Ошибка: {e}. User: {user.id}, Event: {event}"
                )
                return None

            logging.warning(
                f"Ошибка при отправке сообщения админу (попытка {attempt}/{max_retries}): {e}. "
                f"Повтор через {delay:.1f} сек."
            )

            await asyncio.sleep(delay)
            delay *= 2  # Экспоненциальная задержка

        except Exception as e:
            logging.exception(
                f"Неожиданная ошибка при отправке сообщения админу. "
                f"User: {user.id}, Event: {event}"
            )
            return None

    return None