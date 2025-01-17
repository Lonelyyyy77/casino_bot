import sqlite3

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.admin.admin import is_admin
from bot.database.user.user import add_user_to_db, get_user_balance
from bot.start_bot import bot

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


async def start_keyboard(message):
    telegram_id = message.from_user.id
    web_app_url = f"https://8fa6-88-154-11-236.ngrok-free.app?telegram_id={telegram_id}"

    kbds = InlineKeyboardBuilder()
    kbds.row(InlineKeyboardButton(text='Открыть веб приложение', web_app={'url': web_app_url}))
    kbds.row(InlineKeyboardButton(text="Профиль", callback_data="office"))
    kbds.add(InlineKeyboardButton(text='Игры', callback_data='games'))

    if is_admin(message.from_user.id):
        kbds.row(InlineKeyboardButton(text="Админ-панель", callback_data="admin_panel"))

    return kbds.as_markup()


@router.message(CommandStart())
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Не указано"
    keyboard = await start_keyboard(message)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT referrer_id, referral_percent FROM user WHERE id = ?",
        (telegram_id,)
    )
    referrer_data = cursor.fetchone()

    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except ValueError:
            referrer_id = None

    print(f"Referrer ID: {referrer_data}")

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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT has_agreed_rules FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    has_agreed_rules = user_data[0] if user_data else 0

    conn.close()

    if not has_agreed_rules:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text='✅Соглашаюсь✅', callback_data='accept'))

        await message.answer(
            "<b>Нажимая кнопку ниже, вы соглашаетесь с правилами:</b>\n\n"
            "<b>1) Запрещены мульти-аккаунты!</b>\n"
            "<b>2) Запрещены махинации, багаюз!</b>\n"
            "<b>3) Запрещён обман администрации!</b>\n\n"
            "<b><a href='https://telegra.ph/LICENZIONNOE-SOGLAShENIE-WIN-SHARK-01-09'>ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ</a>🧾</b>",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )

        return

    balance_jpc = get_user_balance(telegram_id)
    balance_usd = balance_jpc

    balance_jpc = round(balance_jpc, 3)
    balance_usd = round(balance_usd, 3)

    await message.answer(
        f"Привет! Ваш текущий баланс: {balance_jpc} JPC (${balance_usd}).\nВыберите, что хотите сделать:",
        reply_markup=keyboard
    )

    if is_new_user and referrer_id:
        await notify_referrer(referrer_id, username)


@router.callback_query(lambda c: c.data == 'accept')
async def accept_rules(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    balance_jpc = get_user_balance(telegram_id)
    balance_usd = balance_jpc

    keyboard = await start_keyboard(callback.message)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE user SET has_agreed_rules = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
    except sqlite3.Error as e:
        await callback.message.answer(f"Ошибка обновления базы данных: {e}")
    finally:
        conn.close()

    await callback.message.delete()

    await callback.message.answer(
        f"Привет! Ваш текущий баланс: {balance_jpc} JPC (${balance_usd}).\nВыберите, что хотите сделать:",
        reply_markup=keyboard
    )

