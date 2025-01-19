import sqlite3

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.user.user import update_user_balance

router = Router()


@router.callback_query(lambda c: c.data.startswith("claim_reward_"))
async def reward_button_click(callback: types.CallbackQuery):
    button_id = int(callback.data.split("_")[2])
    user_telegram_id = callback.from_user.id

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT amount, remaining_uses FROM reward_buttons WHERE id = ?", (button_id,))
    button_data = cursor.fetchone()

    if not button_data:
        await callback.answer("Эта кнопка больше недоступна.", show_alert=True)
        conn.close()
        return

    reward_amount, remaining_uses = button_data

    if remaining_uses <= 0:
        await callback.answer("Все награды уже забраны.", show_alert=True)
        conn.close()
        return

    cursor.execute("SELECT id FROM reward_claims WHERE reward_id = ? AND user_id = ?", (button_id, user_telegram_id))
    claim_data = cursor.fetchone()

    if claim_data:
        await callback.answer("Вы уже забрали эту награду.", show_alert=True)
        conn.close()
        return

    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (user_telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.answer("Пользователь не найден в системе.", show_alert=True)
        conn.close()
        return

    new_balance = user_data[0] + reward_amount
    cursor.execute("UPDATE user SET balance = ? WHERE telegram_id = ?", (new_balance, user_telegram_id))

    remaining_uses -= 1
    cursor.execute("UPDATE reward_buttons SET remaining_uses = ? WHERE id = ?", (remaining_uses, button_id))

    cursor.execute("INSERT INTO reward_claims (reward_id, user_id) VALUES (?, ?)", (button_id, user_telegram_id))

    conn.commit()
    conn.close()

    await callback.answer(f"Вы получили {reward_amount} JPC! Ваш новый баланс: {new_balance} JPC.", show_alert=True)

    updated_buttons = InlineKeyboardBuilder()
    updated_buttons.row(InlineKeyboardButton(
        text=f"Забрать {reward_amount} JPC, осталось {remaining_uses}",
        callback_data=f"claim_reward_{button_id}"
    ))

    await callback.message.edit_reply_markup(reply_markup=updated_buttons.as_markup())

