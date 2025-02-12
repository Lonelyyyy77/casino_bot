from aiogram import Router, types
import sqlite3

from aiogram.types import InputMediaPhoto

from bot.database import DB_NAME
from bot.database.user.user import get_menu_image

router = Router()


@router.callback_query(lambda c: c.data == "referral_system")
async def referral_system(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await callback.bot.get_me()).username

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT referral_earnings, referral_percent FROM user WHERE telegram_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        earnings, percent = result
    else:
        earnings, percent = 0, 0

    cursor.execute("SELECT COUNT(*) FROM user WHERE referrer_id = ?", (user_id,))
    referral_count = cursor.fetchone()[0]

    conn.close()

    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    message_text = (
        f"⛓️ <b>Реферальная ссылка:</b> {referral_link}\n"
        f"💸 <b>Заработано на рефералах:</b> {earnings:.2f} JPC\n"
        f"💻 <b>Количество рефералов:</b> {referral_count}\n"
        f"➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"Вы будете получать на баланс <b>{percent}%</b> от пополнений ваших рефералов."
    )

    photo_url = get_menu_image("referral")

    if photo_url:
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=photo_url, caption=message_text, parse_mode="HTML")
            )
        except Exception as e:
            await callback.message.edit_text(message_text, parse_mode="HTML")
    else:
        await callback.message.edit_text(message_text, parse_mode="HTML")
