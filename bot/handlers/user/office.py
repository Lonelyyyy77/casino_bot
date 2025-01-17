import sqlite3

from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == 'office')
async def get_office(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🫰 Реферальная система", callback_data="referral_system"))
    kb.row(InlineKeyboardButton(text="Пополнить баланс", callback_data="replenish"))
    kb.row(InlineKeyboardButton(text="🧶Передача баланс", callback_data="transfer_balance"))

    await callback.message.edit_text('Ваш профиль', reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data == "referral_system")
async def referral_system(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await callback.bot.get_me()).username

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT referral_earnings, referral_percent FROM user WHERE telegram_id = ?", (user_id,))
    earnings, percent = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) FROM user WHERE referrer_id = ?",
        (user_id,)
    )
    referral_count = cursor.fetchone()[0]

    conn.close()

    referral_link = f"https://t.me/{bot_username}?start={user_id}"

    await callback.message.edit_text(
        f"⛓️ Реферальная ссылка: {referral_link}\n"
        f"💸 Заработано на рефералах: {earnings:.2f} JPC\n"
        f"💻 Количество рефералов: {referral_count}\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"Вы будете получать на баланс {percent}% от пополнений ваших рефералов."
    )

