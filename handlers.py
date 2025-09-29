from os import getenv

from dotenv import load_dotenv
from aiogram import Router, Bot, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, CommandStart
from aiogram.types import ChatMemberUpdated, CallbackQuery, Message
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

# Определяем состояния
class UserState(StatesGroup):
    waiting_for_text = State()  # Состояние для хранения текста

sign_button =InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Подписаться на аналитику', url=ANALYTICS_URL)]
])

choice_text = ['Приветствовать', 'Прощаться']
choice_callbacks = ['greet', 'farewell']
choice_button =InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=choice_text[0], callback_data=choice_callbacks[0]),
     InlineKeyboardButton(text=choice_text[1], callback_data=choice_callbacks[1])]])

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
            await send_message_to_admin(bot, get_user_inf(user, event_message.get('add')))
            await send_message_to_admin(bot, event_message.get('greet_message').format(get_user_name(user), ANALYTICS_URL), sign_button)
        except Exception as e:
            logging.error(f"Ошибка при обработке подписки: {e}, user: {event.new_chat_member.user.id}")

@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_left(event: ChatMemberUpdated, bot: Bot):
    if event.chat.id == int(CHANNEL_ID):
        try:
            user = event.old_chat_member.user
            await send_message_to_admin(bot, get_user_inf(user, event_message.get('left')))
            await send_message_to_admin(bot, event_message.get('farewell_message').format(get_user_name(user)), sign_button)
        except Exception as e:
            logging.error(f"Ошибка при обработке отписки: {e}, user: {event.old_chat_member.user.id}")

# Первая функция: обработка текстового сообщения
@router.message(F.text)
async def cmd_new(message: Message, state: FSMContext):
    if str(message.from_user.id) not in ADMIN_LIST:
        await message.answer("Эта команда доступна только администраторам!")
        return

    user_text = message.text.strip().capitalize()
    logging.info(f"Админ {message.from_user.id} отправил текст: {user_text}")

    # Сохраняем текст в состоянии
    await state.update_data(user_text=user_text)

    # Устанавливаем состояние
    await state.set_state(UserState.waiting_for_text)

    # Отвечаем пользователю с кнопкой
    await message.answer(
        text=event_message.get('choice').format(user_text),
        reply_markup=choice_button
    )

# Вторая функция: обработка callback-запроса
@router.callback_query(F.data.in_(choice_callbacks), UserState.waiting_for_text)
async def create_message(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Извлекаем текст из состояния
    data = await state.get_data()
    user_text = data.get('user_text', 'коллега')  # Получаем сохранённый текст
    await callback.answer('Генерирую')

    if callback.data == choice_callbacks[0]:
        await send_message_to_admin(
            bot,
            event_message.get('greet_message').format(user_text, ANALYTICS_URL),
            sign_button
        )
    else:
        await send_message_to_admin(
            bot,
            event_message.get('farewell_message').format(user_text),
            sign_button
        )

    # Очищаем состояние после обработки
    await state.clear()

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

            except Exception as e:
                logging.exception(
                    f"Неожиданная ошибка при отправке сообщения {admin_message[:10]} админу {id_sender}. "
                )
                break  # Переходим к следующему админу

    logging.info(f"Отправлено сообщений {len(sent_messages)} из {len(ADMIN_LIST)} админам")
    return sent_messages