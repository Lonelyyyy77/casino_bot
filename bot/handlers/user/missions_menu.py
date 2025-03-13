import sqlite3

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == 'missions')
async def missions(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()
    balance = user_data[0] if user_data else 0.0

    cursor.execute("SELECT mission_1_status, reward_claimed FROM user_missions WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()

    if result:
        mission_status, reward_claimed = result
    else:
        mission_status, reward_claimed = 0, 0
        cursor.execute("INSERT INTO user_missions (telegram_id) VALUES (?)", (telegram_id,))
        conn.commit()

    progress = min(int((balance / 10) * 100), 100)

    if reward_claimed == 1:
        progress_text = "100% ✅"
    else:
        progress_text = f"{progress}%"

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"Добро пожаловать в игру! ({progress_text})", callback_data="1_mission"))

    await callback.message.answer(
        "Добро пожаловать в игру! Выберите миссию:", reply_markup=kb.as_markup())
