import sqlite3

from aiogram import types, Router
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.admin.admin import is_admin
from math import ceil

router = Router()

PAGE_SIZE = 4


@router.callback_query(lambda c: c.data.startswith("view_users"))
async def view_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции!", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, local_ip, username, language_layout, device, telegram_id, balance, total_bets, is_frizzed_checkout FROM user;")
    users = cursor.fetchall()
    conn.close()

    if not users:
        await callback.message.answer("Пользователи отсутствуют в базе данных.")
        return

    try:
        page = int(callback.data.split(":")[1]) if ":" in callback.data else 1
    except ValueError:
        page = 1

    total_pages = ceil(len(users) / PAGE_SIZE)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    users_on_page = users[start_index:end_index]

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
            f" |- 🔒 Статус счета: {'❄️ Заморожен' if user[8] == 1 else '✅ Активен'}"
            for user in users_on_page
        ]
    )

    kb = InlineKeyboardBuilder()
    for user in users_on_page:
        user_status = '❄️' if user[8] == 1 else '✅'
        kb.row(InlineKeyboardButton(text=f"{user[5]} {user_status}", callback_data=f"toggle_frost_{user[5]}"))

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"view_users:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"view_users:{page + 1}"))
    if nav_buttons:
        kb.row(*nav_buttons)

    await callback.message.edit_text(
        f"Список пользователей (страница {page}/{total_pages}):\n\n{user_list}",
        reply_markup=kb.as_markup()
    )



@router.callback_query(lambda c: c.data.startswith("toggle_frost_"))
async def toggle_frost_handler(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции!", show_alert=True)
        return

    target_id = callback.data.split("_")[-1]

    cursor.execute("SELECT is_frizzed_checkout FROM user WHERE telegram_id = ?", (target_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.answer("Пользователь не найден!", show_alert=True)
        return

    current_status = user_data[0]
    new_status = 1 if current_status == 0 else 0

    cursor.execute(
        "UPDATE user SET is_frizzed_checkout = ? WHERE telegram_id = ?", (new_status, target_id)
    )
    conn.commit()

    status_text = "❄️ Заморожен" if new_status == 1 else "✅ Активен"
    await callback.answer(f"Статус пользователя {target_id} изменён на: {status_text}", show_alert=True)

    # Обновляем список пользователей на текущей странице
    await view_users(callback)
