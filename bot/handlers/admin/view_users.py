import sqlite3

from aiogram import types, Router

from bot.database import DB_NAME
from bot.database.admin.admin import is_admin

router = Router()


@router.callback_query(lambda c: c.data == "view_users")
async def view_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции!", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, local_ip, username, language_layout, device, telegram_id, balance, total_bets FROM user;")
    users = cursor.fetchall()
    conn.close()

    if not users:
        await callback.message.answer("Пользователи отсутствуют в базе данных.")
        return

    user_list = "\n".join(
        [
            f"{user[0]}:\n"
            f" |- 👤 @{user[2]}\n"
            f" |- DEVICE📱 - {user[4]}\n"
            f" |- IP📡 - {user[1]}\n"
            f" |- 🆔 (#id_{user[5]})\n"
            f" |- 🌍 {user[3].upper()}\n"
            f" |- 🏦 {round(user[6], 3)} JPC | {round(user[6], 3)}$\n"
            f" |- 💸 Потрачено на ставки: {round(user[7], 3)} JPC\n"
            for user in users
        ]
    )

    await callback.message.answer(f"Список пользователей:\n\n{user_list}")

