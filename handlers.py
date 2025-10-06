from os import getenv

from dotenv import load_dotenv
from aiogram import Router, Bot, types, F
from aiogram.utils.keyboard import InlineKeyboardMarkup
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, CommandStart
from aiogram.types import ChatMemberUpdated, Message
from aiogram.exceptions import TelegramAPIError
from utils import get_user_inf, event_message, get_user_name
import asyncio
import logging

router = Router()

# Глобальные переменные
load_dotenv()
ADMIN_ID = getenv("ADMIN_ID")
OWNER_ID = getenv("OWNER_ID")
ADMIN_LIST = [id_ for id_ in [ADMIN_ID, OWNER_ID] if id_ is not None]
if not ADMIN_LIST:
    logging.error("ADMIN_LIST пуст! Проверьте ADMIN_ID и OWNER_ID в .env")
    raise ValueError("ADMIN_LIST не может быть пустым")

CHANNEL_ID = getenv("CHANNEL_ID")
if not CHANNEL_ID:
    logging.error("CHANNEL_ID не задан в .env")
    raise ValueError("CHANNEL_ID обязателен")

SIGN_URL = getenv("SIGN_URL")
ANALYTICS_URL = getenv("ANALYTICS_URL")
if not SIGN_URL or not ANALYTICS_URL:
    logging.error("SIGN_URL или ANALYTICS_URL не заданы в .env")
    raise ValueError("SIGN_URL и ANALYTICS_URL обязательны")

# Исключения для повторных попыток
RETRY_EXC = (
    TelegramAPIError,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError
)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    logging.info(f"Пользователь {message.from_user.id} отправил /start")
    await message.answer(f"👋 Теперь я смогу отправлять вам уведомления!")

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_joined(event: ChatMemberUpdated, bot: Bot):
    if event.chat.id == int(CHANNEL_ID):
        try:
            user = event.new_chat_member.user
            await send_message_to_admin(
                bot,
                get_user_inf(user, event_message.get('add'))
            )
            await send_message_to_admin(
                bot,
                event_message.get('greet_message').format(get_user_name(user), ANALYTICS_URL, SIGN_URL)
            )
        except Exception as e:
            logging.error(f"Ошибка при обработке подписки: {e}, user: {event.new_chat_member.user.id}")

@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_left(event: ChatMemberUpdated, bot: Bot):
    if event.chat.id == int(CHANNEL_ID):
        try:
            user = event.old_chat_member.user
            await send_message_to_admin(
                bot,
                get_user_inf(user, event_message.get('left'))
            )
            await send_message_to_admin(
                bot,
                event_message.get('farewell_message').format(get_user_name(user), SIGN_URL)
            )
        except Exception as e:
            logging.error(f"Ошибка при обработке отписки: {e}, user: {event.old_chat_member.user.id}")

@router.message(F.text)
async def cmd_new(message: Message):
    if str(message.from_user.id) not in ADMIN_LIST:
        await message.answer("Эта команда доступна только администраторам!")
        return

    user_text = message.text.strip().capitalize()
    logging.info(f"Админ {message.from_user.id} отправил текст: {user_text}")

    await message.answer(
            event_message.get('greet_message').format(user_text, ANALYTICS_URL, SIGN_URL),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    await message.answer(
            event_message.get('farewell_message').format(user_text, SIGN_URL),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

async def send_message_to_admin(
        bot: Bot,
        admin_message: str,
        keyboard: InlineKeyboardMarkup | None = None,
        max_retries: int = 3,
        initial_delay: float = 1.0
) -> list[types.Message]:
    """
    Отправляет сообщение всем админам с обработкой ошибок и повторными попытками

    Args:
        bot: Экземпляр бота
        admin_message: Сообщение
        keyboard: Клавиатура или None
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка между попытками

    Returns:
        Список отправленных сообщений
    """

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
                    disable_web_page_preview=True,
                    reply_markup=keyboard
                )
                logging.info(f"Сообщение {admin_message[:10]} админу {id_sender} отправлено успешно (попытка {attempt + 1})")
                sent_messages.append(message)
                break  # Переходим к следующему админу

            except RETRY_EXC as e:
                attempt += 1
                if attempt >= max_retries:
                    logging.error(
                        f"Не удалось отправить сообщение {admin_message[:10]} админу {id_sender} после {max_retries} попыток. "
                    )
                    break

                logging.warning(
                    f"Ошибка при отправке сообщения админу {id_sender} (попытка {attempt}/{max_retries}): {e}. "
                    f"Повтор через {delay:.1f} сек."
                )

                await asyncio.sleep(delay)
                delay *= 2  # Экспоненциальная задержка

            except Exception as er:
                logging.exception(
                    f"Неожиданная ошибка при отправке сообщения {admin_message[:10]} админу {id_sender}: {str(er)}. "
                )
                break  # Переходим к следующему админу

    logging.info(f"Отправлено сообщений {len(sent_messages)} из {len(ADMIN_LIST)} админам")
    return sent_messages