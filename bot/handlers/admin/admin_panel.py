from aiogram import Router, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.admin.admin import is_admin, get_user_statistics

router = Router()


@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции!", show_alert=True)
        return

    stats = get_user_statistics()

    stats_message = (
        f"👥 Статистика пользователей:\n\n"
        f"📅 За последние 24 часа: {stats['last_day']}\n"
        f"📅 За последние 7 дней: {stats['last_week']}\n"
        f"📅 За последний месяц: {stats['last_month']}\n"
        f"👤 Всего пользователей: {stats['total']}\n"
    )

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Посмотреть всех пользователей", callback_data="view_users"))
    kb.row(InlineKeyboardButton(text="Сделать рассылку", callback_data="mailing"))

    await callback.message.answer(stats_message, reply_markup=kb.as_markup())
