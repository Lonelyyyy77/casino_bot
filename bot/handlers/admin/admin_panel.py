from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InputMediaPhoto, InputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.admin.admin import is_admin, get_user_statistics
from bot.database.user.user import get_menu_image

router = Router()


@router.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()

    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа к этой функции!", show_alert=True)
        return

    stats = get_user_statistics()

    stats_message = (
        f"👥 <b>Статистика пользователей:</b>\n\n"
        f"📅 <b>За последние 24 часа:</b> {stats['last_day']}\n"
        f"📅 <b>За последние 7 дней:</b> {stats['last_week']}\n"
        f"📅 <b>За последний месяц:</b> {stats['last_month']}\n"
        f"👤 <b>Всего пользователей:</b> {stats['total']}\n"
    )

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👥 Посмотреть всех пользователей", callback_data="view_users"))
    kb.row(InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="mailing"),
           InlineKeyboardButton(text="⚙️ Настройки рассылки", callback_data='mailing_settings'))
    kb.row(InlineKeyboardButton(text="💰 Настроить реферальный процент", callback_data="adjust_referral_percent"))
    kb.row(InlineKeyboardButton(text='⚙️ Установить процент выигрыша', callback_data='set_global_percentage'))
    kb.row(InlineKeyboardButton(text='🖼 Установить картинку для меню', callback_data='admin_set_image'))
    kb.row(InlineKeyboardButton(text="🎟 Создать промокод", callback_data="create_promo"),
           InlineKeyboardButton(text="⚙️ Настройка промокодов", callback_data='promo_settings'))
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data='home'))

    admin_panel_image = get_menu_image("panel")

    if admin_panel_image:
        try:
            photo = admin_panel_image if isinstance(admin_panel_image, str) else InputFile(admin_panel_image)

            if callback.message.photo:
                media = InputMediaPhoto(media=photo, caption=stats_message, parse_mode="HTML")
                await callback.message.edit_media(media=media, reply_markup=kb.as_markup())
            else:
                await callback.message.edit_text(stats_message, reply_markup=kb.as_markup(), parse_mode="HTML")
        except TelegramBadRequest:
            await callback.message.answer(stats_message, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        try:
            await callback.message.edit_text(stats_message, reply_markup=kb.as_markup(), parse_mode="HTML")
        except TelegramBadRequest:
            await callback.message.answer(stats_message, reply_markup=kb.as_markup(), parse_mode="HTML")