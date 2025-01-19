import sqlite3

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database import DB_NAME
from bot.database.admin.admin import is_admin
from bot.states.admin.states import SetPercentageStates

router = Router()


def get_global_percentage():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('SELECT percentage FROM settings WHERE id = 1')
    result = cursor.fetchone()
    if result:
        return result[0]
    return 10.0


@router.callback_query(lambda c: c.data == 'set_global_percentage')
async def initiate_set_percentage(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав для выполнения этой команды.")
        return

    await state.set_state(SetPercentageStates.waiting_for_percentage)
    await callback.message.answer("Пожалуйста, введите новый процент")
    await callback.answer()


@router.message(SetPercentageStates.waiting_for_percentage)
async def process_new_percentage(message: types.Message, state: FSMContext):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if not is_admin(message.from_user.id):
        await message.reply("У вас нет прав для выполнения этой команды.")
        await state.clear()
        return

    try:
        percentage = float(message.text)
        if not (0 <= percentage <= 100):
            raise ValueError("Percentage out of bounds")
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число от 0 до 100.")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM game_settings WHERE id = 1")
        result = cursor.fetchone()

        if result:
            cursor.execute('UPDATE game_settings SET percentage = ? WHERE id = 1', (percentage,))
            await message.reply(f"Глобальный процент успешно обновлён на {percentage}%.")
        else:
            cursor.execute('INSERT INTO game_settings (id, percentage) VALUES (?, ?)', (1, percentage))
            await message.reply(f"Глобальный процент успешно установлен на {percentage}%.")

        conn.commit()
    except sqlite3.Error as e:
        await message.reply(f"Произошла ошибка при работе с базой данных: {e}")
    finally:
        if conn:
            conn.close()

    await state.clear()


