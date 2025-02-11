import sqlite3

from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.user.user import get_menu_image

router = Router()


@router.callback_query(lambda c: c.data == 'office')
async def get_office(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🫰 Реферальная система", callback_data="referral_system"))
    kb.row(InlineKeyboardButton(text="📥 Пополнить баланс", callback_data="replenish"))
    kb.add(InlineKeyboardButton(text="📤 Вывести баланс", callback_data='checkout_balance'))
    kb.row(InlineKeyboardButton(text="🧶 Передача баланса", callback_data="transfer_balance"))
    kb.row(InlineKeyboardButton(text="🎟 Активировать промокод", callback_data='activate_promo'))
    kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data='home'))

    # Получаем изображение для личного кабинета из БД
    profile_image = get_menu_image("profile")

    text = (
        f"<b>👤 Ваш профиль</b>\n\n"
        f"Привет, <b>{callback.from_user.first_name}</b>! Добро пожаловать в твой личный кабинет.\n"
        f"👉 Выбери нужный раздел из меню ниже:"
    )

    if profile_image:
        media = InputMediaPhoto(media=profile_image, caption=text, parse_mode="HTML")
        await callback.message.edit_media(media, reply_markup=kb.as_markup())
    else:
        await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")





