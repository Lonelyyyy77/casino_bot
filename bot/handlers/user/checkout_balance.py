from aiogram import Router
from aiogram.types import CallbackQuery
import sqlite3

from bot.database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == 'checkout_balance')
async def checkout_balance_handler(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    telegram_id = callback.from_user.id

    cursor.execute("SELECT is_frizzed_checkout FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    is_frizzed_checkout = user_data[0]

    if is_frizzed_checkout == 1:
        await callback.answer("Доступ к выводу средств заблокирован. Обратитесь в поддержку.", show_alert=True)
        return

    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (telegram_id,))
    balance_data = cursor.fetchone()
    if balance_data:
        balance = balance_data[0]
        await callback.message.answer(f"Ваш доступный баланс для вывода: {balance:.2f} USDT")
    else:
        await callback.message.answer("Не удалось получить информацию о вашем балансе.")
