import sqlite3

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_NAME
from states.admin.states import ReferralSettingsState

router = Router()


@router.callback_query(lambda c: c.data == "adjust_referral_percent")
async def adjust_referral_percent(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="Изменить для всех", callback_data="change_percent_all"))
    kb.row(InlineKeyboardButton(text="Изменить для пользователя", callback_data="change_percent_user"))

    await callback.message.edit_text(
        "Выберите действие:\n\n"
        "1️⃣ Изменить процент для всех пользователей\n"
        "2️⃣ Изменить процент для конкретного пользователя", reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data == "change_percent_all")
async def change_percent_all(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новый процент реферальных выплат для всех пользователей (например, 10):")
    await state.set_state(ReferralSettingsState.change_percent_all)


@router.message(ReferralSettingsState.change_percent_all)
async def save_percent_all(message: types.Message, state: FSMContext):
    try:
        new_percent = float(message.text)
        if new_percent < 0 or new_percent > 100:
            raise ValueError("Процент должен быть от 0 до 100.")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE user SET referral_percent = ?", (new_percent,))
        conn.commit()
        conn.close()

        await message.answer(f"Процент реферальных выплат для всех пользователей обновлён на {new_percent}%.")
        await state.clear()
    except ValueError:
        await message.answer("Введите корректное число от 0 до 100.")


@router.callback_query(lambda c: c.data == "change_percent_user")
async def change_percent_user(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите ID пользователя и новый процент в формате `ID:Процент` (например, 123456789:10):",
        parse_mode="Markdown"
    )
    await state.set_state(ReferralSettingsState.change_percent_user)


@router.message(ReferralSettingsState.change_percent_user)
async def save_percent_user(message: types.Message, state: FSMContext):
    try:
        user_data = message.text.split(":")
        user_id = int(user_data[0].strip())
        new_percent = float(user_data[1].strip())

        if new_percent < 0 or new_percent > 100:
            raise ValueError("Процент должен быть от 0 до 100.")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE user SET referral_percent = ? WHERE telegram_id = ?", (new_percent, user_id))
        if cursor.rowcount == 0:
            await message.answer(f"Пользователь с ID {user_id} не найден.")
        else:
            await message.answer(f"Процент реферальных выплат для пользователя {user_id} обновлён на {new_percent}%.")
        conn.commit()
        conn.close()

        await state.clear()
    except (ValueError, IndexError):
        await message.answer("Введите данные в формате `ID:Процент` (например, 123456789:10).")
