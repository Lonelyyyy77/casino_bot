import sqlite3

from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == 'office')
async def get_office(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🫰 Реферальная система", callback_data="referral_system"))
    kb.row(InlineKeyboardButton(text="Пополнить баланс", callback_data="replenish"))
    kb.row(InlineKeyboardButton(text="🧶Передача баланс", callback_data="transfer_balance"))
    kb.row(InlineKeyboardButton(text="Вывести баланс", callback_data='checkout_balance'))
    kb.row(InlineKeyboardButton(text="Назад", callback_data='home'))

    await callback.message.edit_text('Ваш профиль', reply_markup=kb.as_markup())




