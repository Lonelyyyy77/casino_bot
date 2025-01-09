from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='Игры', callback_data='games'))

    await message.answer("Привет выбери что хочешь сделать:", reply_markup=kb.as_markup())
