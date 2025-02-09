import sqlite3
import random
from itertools import zip_longest
from typing import Union

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_NAME
from database.admin.admin import is_admin
from database.user.user import add_user_to_db, get_user_balance
from start_bot import bot

router = Router()


async def notify_referrer(referrer_id: int, new_user: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT telegram_id FROM user WHERE id = ?", (referrer_id,))
    referrer_data = cursor.fetchone()
    conn.close()

    if referrer_data:
        referrer_telegram_id = referrer_data[0]
        await bot.send_message(
            referrer_telegram_id,
            f"🐬 Ваш реферал {new_user} успешно зарегистрировался!"
        )



async def start_keyboard(user_id: int):
    """
    Создаем Inline-клавиатуру, в которой web_app_url формируется,
    используя переданный user_id напрямую.
    """
    web_app_url = f"https://2dfa-91-234-26-148.ngrok-free.app?telegram_id={user_id}"

    kbds = InlineKeyboardBuilder()
    kbds.row(
        InlineKeyboardButton(
            text='Открыть веб приложение',
            web_app={'url': web_app_url}
        )
    )
    kbds.row(InlineKeyboardButton(text="Профиль", callback_data="office"))
    kbds.add(InlineKeyboardButton(text='Игры', callback_data='games'))

    if is_admin(user_id):
        kbds.row(InlineKeyboardButton(text="Админ-панель", callback_data="admin_panel"))

    return kbds.as_markup()

# ------------------- Хендлер на /start -------------------
@router.message(CommandStart())
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Не указано"

    # сразу генерируем клавиатуру по user_id
    keyboard = await start_keyboard(telegram_id)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT has_agreed_rules, has_completed_captcha FROM user WHERE telegram_id = ?",
        (telegram_id,)
    )
    user_data = cursor.fetchone()

    if not user_data:
        # пользователь новый
        referrer_id = None
        if message.text and len(message.text.split()) > 1:
            try:
                referrer_id = int(message.text.split()[1])
            except ValueError:
                referrer_id = None

        local_ip = "Неизвестно"
        device = "Неизвестно"
        language_layout = message.from_user.language_code

        is_new_user = add_user_to_db(
            db_name=DB_NAME,
            telegram_id=telegram_id,
            local_ip=local_ip,
            username=username,
            language_layout=language_layout,
            device=device,
            referrer_id=referrer_id,
        )

        has_agreed_rules = 0
        has_completed_captcha = 0
    else:
        has_agreed_rules, has_completed_captcha = user_data
        is_new_user = False

    conn.close()

    if not has_agreed_rules:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text='✅Соглашаюсь✅', callback_data='accept'))

        await message.answer(
            "<b>Нажимая кнопку ниже, вы соглашаетесь с правилами:</b>\n\n"
            "<b>1) Запрещены мульти-аккаунты!</b>\n"
            "<b>2) Запрещены махинации, багаюз!</b>\n"
            "<b>3) Запрещён обман администрации!</b>\n\n"
            "<b><a href='https://telegra.ph/LICENZIONNOE-SOGLAShENIE-WIN-SHARK-01-09'>ЛИЦЕНЗИОННОЕ СОГЛАСШЕНИЕ</a>🧾</b>",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        return

    if not has_completed_captcha:
        await start_captcha(message)
        return

    balance_jpc = get_user_balance(telegram_id)
    balance_usd = balance_jpc
    balance_jpc = round(balance_jpc, 3)
    balance_usd = round(balance_usd, 3)

    await message.answer(
        f"Привет! Ваш текущий баланс: {balance_jpc} JPC (${balance_usd}).\n"
        f"Выберите, что хотите сделать:",
        reply_markup=keyboard
    )

    if is_new_user and referrer_id:
        await notify_referrer(referrer_id, username)

# ------------------- Принятие правил -------------------
@router.callback_query(lambda c: c.data == "accept")
async def accept_rules(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE user SET has_agreed_rules = 1 WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()

    await callback.message.delete()
    # Отправляем пользователя на капчу
    await start_captcha(callback)

# ------------------- Обработка нажатия по капче -------------------
@router.callback_query(lambda c: c.data.startswith("captcha:"))
async def captcha_handler(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    selected_fruit = callback.data.split(":")[1]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expected_answer FROM captcha WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()

    if not result:
        await callback.answer("Ошибка капчи. Попробуйте снова.", show_alert=True)
        conn.close()
        return

    expected_fruit = result[0]

    if selected_fruit == expected_fruit:
        # Удаляем запись капчи и ставим флаг, что капча пройдена
        cursor.execute("DELETE FROM captcha WHERE telegram_id = ?", (telegram_id,))
        cursor.execute("UPDATE user SET has_completed_captcha = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        conn.close()

        await callback.message.delete()

        # (!) Генерируем клавиатуру, передавая user_id напрямую
        keyboard = await start_keyboard(telegram_id)
        await callback.message.answer(
            "Капча успешно пройдена! Добро пожаловать!",
            reply_markup=keyboard
        )
    else:
        conn.close()
        await callback.answer("Неправильный выбор. Попробуйте ещё раз.", show_alert=True)

# ------------------- Функция показа капчи -------------------
async def start_captcha(source: Union[types.CallbackQuery, types.Message]):
    """
    Функция, которая отправляет капчу. Принимает либо CallbackQuery, либо Message.
    """
    telegram_id = source.from_user.id

    fruits = ["🍎", "🍌", "🍇", "🍍", "🍓", "🍒", "🥝", "🍑", "🍊", "🍋", "🍈", "🍉"]
    selected_fruit = random.choice(fruits)
    expected_fruit = selected_fruit

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO captcha (telegram_id, expected_answer) VALUES (?, ?)",
        (telegram_id, expected_fruit)
    )
    conn.commit()
    conn.close()

    kb = InlineKeyboardBuilder()
    for row in zip_longest(*[iter(fruits)] * 4, fillvalue=None):
        buttons = [
            InlineKeyboardButton(text=fruit, callback_data=f"captcha:{fruit}")
            for fruit in row if fruit
        ]
        kb.row(*buttons)

    caption_text = f"Для подтверждения, выберите правильный фрукт: {selected_fruit}"
    if isinstance(source, types.CallbackQuery):
        await source.message.answer(caption_text, reply_markup=kb.as_markup())
    elif isinstance(source, types.Message):
        await source.answer(caption_text, reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data == 'home')
async def home(source: Union[types.CallbackQuery, types.Message]):
    telegram_id = source.from_user.id

    balance_jpc = get_user_balance(telegram_id)
    balance_usd = balance_jpc

    balance_jpc = round(balance_jpc, 3)
    balance_usd = round(balance_usd, 3)

    keyboard = await start_keyboard(source.message)

    if isinstance(source, types.CallbackQuery):
        await source.message.edit_text(
            f"Привет! Ваш текущий баланс: {balance_jpc} JPC (${balance_usd}).\nВыберите, что хотите сделать:",
            reply_markup=keyboard
        )
    elif isinstance(source, types.Message):
        await source.answer(
            f"Привет! Ваш текущий баланс: {balance_jpc} JPC (${balance_usd}).\nВыберите, что хотите сделать:",
            reply_markup=keyboard
        )
