from os import getenv
from dotenv import load_dotenv
from aiogram import Router
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.types import ChatMemberUpdated
from aiogram.filters import CommandStart
from utils import give_user_inf, event_message
import asyncio
import logging
from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError

router = Router()

# Глобальные переменные
load_dotenv()
ADMIN_ID = getenv("ADMIN_ID")
OWNER_ID = getenv("OWNER_ID")
ADMIN_LIST = [ADMIN_ID, OWNER_ID]
CHANNEL_ID = getenv("CHANNEL_ID")

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"👋 Теперь я смогу отправлять вам уведомления!")

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
) -> list[types.Message]:
    """
    Отправляет сообщение всем админам с обработкой ошибок и повторными попытками

    Args:
        bot: Экземпляр бота
        user: Пользователь
        event: Событие
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка между попытками

    Returns:
        Список отправленных сообщений
    """
    user_inf = await give_user_inf(user)
    admin_message = f'{event}\n{user_inf}'

    sent_messages = []

    for id_sender in ADMIN_LIST:
        delay = initial_delay
        attempt = 0

        while attempt < max_retries:
            try:
                message = await bot.send_message(
                    chat_id=id_sender,
                    text=admin_message,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                logging.info(f"Сообщение админу {id_sender} отправлено успешно (попытка {attempt + 1}), о юзере {user.id}")
                sent_messages.append(message)
                break  # Переходим к следующему админу

            except RETRY_EXC as e:
                attempt += 1
                if attempt >= max_retries:
                    logging.error(
                        f"Не удалось отправить сообщение админу {id_sender} после {max_retries} попыток. "
                        f"Ошибка: {e}. User: {user.id}, Event: {event}"
                    )
                    break

                logging.warning(
                    f"Ошибка при отправке сообщения админу {id_sender} (попытка {attempt}/{max_retries}): {e}. "
                    f"Повтор через {delay:.1f} сек."
                )

                await asyncio.sleep(delay)
                delay *= 2  # Экспоненциальная задержка

            except Exception as e:
                logging.exception(
                    f"Неожиданная ошибка при отправке сообщения админу {id_sender}. "
                    f"User: {user.id}, Event: {event}"
                )
                break  # Переходим к следующему админу

    logging.info(f"Отправлено сообщений {len(sent_messages)} из {len(ADMIN_LIST)} админам")
    return sent_messages
