from aiogram import Router, types
import sqlite3

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == '1_mission')
async def start_mission(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if user_data and user_data[0] >= 10.0:
        cursor.execute("UPDATE user_missions SET mission_1_status = 2 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        progress_text = "100% ✅"
        reward_button = InlineKeyboardButton(text="Забрать награду", callback_data="1_ms_claim")
    else:
        cursor.execute("UPDATE user_missions SET mission_1_status = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        progress_text = "50%"
        reward_button = InlineKeyboardButton(text="Забрать награду (недоступно)", callback_data="disabled")

    kb = InlineKeyboardBuilder()
    kb.row(reward_button)

    await callback.message.edit_text(
        'Вы впервые в нашем казино-боте. Первый шаг — пополнить баланс и получить свой «стартовый капитал» для дальнейших приключений!\n\n'
        'Условия задания:\n'
        '1. Пополните баланс на 10 USDT или больше одним платежом.\n'
        '2. Дождитесь подтверждения, что средства поступили на счёт (обычно это занимает не более 2–3 минут).\n'
        '3. Не выводите деньги, пока задание не будет отмечено как выполненное.', reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data == '1_ms_claim')
async def claim_reward(callback: types.CallbackQuery):
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
        await callback.answer("❌ Ошибка: Задание не найдено.", show_alert=True)
        return

    if balance >= 10.0 and mission_status == 2 and reward_claimed == 0:
        cursor.execute("UPDATE user SET balance = balance + 0.1 WHERE telegram_id = ?", (telegram_id,))
        cursor.execute("UPDATE user_missions SET reward_claimed = 1 WHERE telegram_id = ?", (telegram_id,))
        conn.commit()

        await callback.message.edit_text("✅ Вы успешно забрали награду: 0.1 JPC!")
    elif balance < 10.0:
        await callback.answer("❌ Вы ещё не пополнили баланс на 10 USDT!", show_alert=True)
    elif reward_claimed == 1:
        await callback.answer("❌ Вы уже получили награду.", show_alert=True)
    else:
        await callback.answer("❌ Задание не завершено.", show_alert=True)

    conn.close()