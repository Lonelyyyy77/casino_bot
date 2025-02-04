import asyncio
import re

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
import sqlite3

from aiogram.utils.keyboard import InlineKeyboardBuilder
from pyexpat.errors import messages

from bot.database import DB_NAME
from bot.start_bot import crypto
from bot.states.user.user import WithdrawStates

router = Router()


@router.callback_query(lambda c: c.data == 'checkout_balance')
async def checkout_balance_handler(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    telegram_id = callback.from_user.id

    cursor.execute("SELECT is_frizzed_checkout, balance FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        conn.close()
        return

    is_frizzed_checkout, balance = user_data

    if is_frizzed_checkout == 1:
        await callback.answer("Доступ к выводу средств заблокирован. Обратитесь в поддержку.", show_alert=True)
        conn.close()
        return

    # Отправляем сообщение с балансом и inline-кнопками для вывода
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="2$", callback_data="withdraw_2"),
        InlineKeyboardButton(text="5$", callback_data="withdraw_5"),
        InlineKeyboardButton(text="10$", callback_data="withdraw_10"),
        InlineKeyboardButton(text="Ввести сумму", callback_data="withdraw_manual")
    )
    await callback.message.answer(f"Ваш доступный баланс для вывода: {balance:.2f} USDT\n\nВыберите сумму для вывода:",
                                  reply_markup=keyboard.as_markup())
    conn.close()


@router.callback_query(lambda c: c.data.startswith("withdraw_"))
async def fixed_withdraw_handler(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id

    # Определяем сумму на основании callback_data
    data = callback.data
    if data == "withdraw_2":
        amount = 2.0
    elif data == "withdraw_5":
        amount = 5.0
    elif data == "withdraw_10":
        amount = 10.0
    elif data == "withdraw_manual":
        await callback.message.answer("Введите сумму для вывода (в USDT):")
        await state.set_state(WithdrawStates.waiting_for_amount)
        return
    else:
        await callback.answer("Неверная команда.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    if not result:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        conn.close()
        return

    balance = result[0]

    if balance < amount:
        await callback.answer("Недостаточно средств для вывода.", show_alert=True)
        conn.close()
        return

    new_balance = balance - amount
    cursor.execute("UPDATE user SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

    try:
        check = await crypto.create_check(asset='USDT', amount=amount)
    except Exception as e:
        await callback.message.answer("Ошибка при создании чека")
        return

    check_str = str(check)
    pattern = r"bot_check_url='([^']+)'"
    match = re.search(pattern, check_str)

    if match:
        link = match.group(1)
    else:
        link = "Не удалось найти ссылку"

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Получить", url=link))

    response_text = (
        "Чек успешно создан!\n"
        f"Сумма: {amount:.2f} USDT\n"
        f"Чек ID: {check.check_id}\n"
    )

    await callback.message.answer(response_text, reply_markup=kb.as_markup())
    await asyncio.sleep(15)
    await callback.message.delete()


@router.message(WithdrawStates.waiting_for_amount)
async def process_manual_withdraw(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть положительной.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    if not result:
        await message.answer("Ошибка: пользователь не найден.")
        conn.close()
        await state.clear()
        return

    balance = result[0]
    if balance < amount:
        await message.answer("Недостаточно средств для вывода.")
        conn.close()
        await state.clear()
        return

    new_balance = balance - amount
    cursor.execute("UPDATE user SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

    try:
        check = await crypto.create_check(asset='USDT', amount=amount)
    except Exception as e:
        await message.answer("Ошибка при создании чека")
        await state.clear()
        return

    check_str = str(check)
    pattern = r"bot_check_url='([^']+)'"
    match = re.search(pattern, check_str)

    if match:
        link = match.group(1)
    else:
        link = "Не удалось найти ссылку"

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text='Получить', url=link))

    response_text = (
        "Чек успешно создан!\n"
        f"Сумма: {amount:.2f} USDT\n"
        f"Чек ID: {check.check_id}\n"
    )

    await message.answer(response_text, reply_markup=kb.as_markup())
    await state.clear()
    await asyncio.sleep(15)
    await message.delete()
