import asyncio
import random

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


@router.callback_query(lambda c: c.data == 'games')
async def games(callback: CallbackQuery):
    await callback.message.edit_text('Выберете игру:', reply_markup=get_game_keyboard())


@router.callback_query(lambda c: c.data in ['bones_game', 'basketball_game', 'bowling_game'])
async def game_selected(callback: CallbackQuery):
    text = "Вы выбрали игру: " + callback.data.replace("_", " ").title()

    game_message = await callback.message.answer(text)
    kb = get_game_keyboard()

    if callback.data == 'bones_game':
        result = random.randint(1, 6)
        await game_message.edit_text(f"🎲 Вы выбросили: {result}\nПопробуйте ещё раз!", reply_markup=kb)

    elif callback.data == 'basketball_game':
        result = random.randint(1, 6)
        if result > 3:
            message_text = f"🏀 Отличный бросок! Вы набрали {result} очков! 🏆\nПопробуйте ещё раз!"
        else:
            message_text = f"🏀 Не повезло, всего {result} очка. 😢 Попробуйте ещё раз!"
        await game_message.edit_text(message_text, reply_markup=kb)

    elif callback.data == 'bowling_game':
        result = random.randint(0, 10)
        if result == 10:
            message_text = "🎳 🎉 Страйк! Вы выбили все кегли!\nПопробуйте ещё раз!"
        else:
            message_text = f"🎳 Вы выбили {result} кеглей. Неплохо!\nПопробуйте ещё раз!"
        await game_message.edit_text(message_text, reply_markup=kb)


def get_game_keyboard():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text='🎲', callback_data='bones_game'))
    kb.add(InlineKeyboardButton(text='🏀', callback_data='basketball_game'))
    kb.add(InlineKeyboardButton(text='🎳', callback_data='bowling_game'))
    return kb.as_markup()