from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import Router
import sqlite3

from bot.database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == "promo_settings")
async def promo_settings(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM promo_codes WHERE used_activations >= max_activations")
    conn.commit()

    cursor.execute(
        "SELECT code, bonus_amount, max_activations, used_activations, expiration_date FROM promo_codes "
        "WHERE expiration_date > datetime('now')"
    )
    promo_codes = cursor.fetchall()
    conn.close()

    if not promo_codes:
        await callback.message.edit_text("⚠️ Нет активных промокодов.")
        return

    promo_text = "🎟 <b>Активные промокоды:</b>\n\n"
    buttons = []

    for promo in promo_codes:
        code, bonus_amount, max_activations, used_activations, expiration_date = promo
        remaining_activations = max_activations - used_activations

        if remaining_activations <= 0:
            continue

        promo_text += (
            f"🔹 <b>{code}</b>\n"
            f"💰 Бонус: {bonus_amount:.2f} USDT\n"
            f"🔄 Осталось активаций: {remaining_activations}/{max_activations}\n"
            f"📅 Действует до: {expiration_date}\n\n"
        )

        buttons.append(InlineKeyboardButton(text=f"❌ Удалить {code}", callback_data=f"delete_promo:{code}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])

    await callback.message.edit_text(promo_text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(lambda c: c.data.startswith("delete_promo:"))
async def delete_promo(callback: CallbackQuery):
    promo_code = callback.data.split(":")[1]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM promo_codes WHERE code = ?", (promo_code,))
    conn.commit()
    conn.close()

    await callback.answer(f"✅ Промокод {promo_code} удалён.", show_alert=True)

    await promo_settings(callback)
