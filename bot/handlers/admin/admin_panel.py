from aiogram import Router, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.admin.admin import is_admin

router = Router()


@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции!", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Посмотреть всех пользователей", callback_data="view_users"))

    await callback.message.answer("Добро пожаловать в админ-панель!", reply_markup=kb.as_markup())
