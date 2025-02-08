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


import sqlite3
import asyncio
import logging
import re
from aiogram import Bot, types
from aiogram.types import InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web


@router.callback_query(lambda c: c.data == 'checkout_balance')
async def checkout_balance_handler(callback: types.CallbackQuery):
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

    # Клавиатура для вывода
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="2$", callback_data="withdraw_2"),
        InlineKeyboardButton(text="5$", callback_data="withdraw_5"),
        InlineKeyboardButton(text="10$", callback_data="withdraw_10"),
        InlineKeyboardButton(text="Ввести сумму", callback_data="withdraw_manual")
    )

    await callback.message.answer(
        f"Ваш доступный баланс для вывода: {balance:.2f} USDT\n\nВыберите сумму для вывода:",
        reply_markup=keyboard.as_markup()
    )
    conn.close()


### 💸 **Обработчик вывода фиксированных сумм**
@router.callback_query(lambda c: c.data.startswith("withdraw_"))
async def fixed_withdraw_handler(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    username = callback.from_user.username or f"ID: {telegram_id}"

    # Определяем сумму
    data = callback.data
    amount_map = {
        "withdraw_2": 2.0,
        "withdraw_5": 5.0,
        "withdraw_10": 10.0
    }
    amount = amount_map.get(data)

    if data == "withdraw_manual":
        await callback.message.answer("Введите сумму для вывода (в USDT):")
        await state.set_state(WithdrawStates.waiting_for_amount)
        return
    if not amount:
        await callback.answer("Неверная команда.", show_alert=True)
        return

    # Проверяем баланс
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

        log_message = (f"🚨 *Попытка вывода отклонена!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Недостаточно средств (Баланс: {balance:.2f} USDT)")
        await bot.send_message(CHANNEL_ID, log_message)
        return

    # Обновляем баланс пользователя
    new_balance = balance - amount
    cursor.execute("UPDATE user SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

    ### 🏦 **Создание чека CryptoBot**
    try:
        logging.info(f"📤 Отправка запроса на создание чека: {amount} USDT")
        check = await crypto.create_check(asset='USDT', amount=str(amount))  # Передаём сумму как строку
    except Exception as e:
        logging.error(f"❌ Ошибка при создании чека: {e}")
        await callback.message.answer("Ошибка при создании чека")

        log_message = (f"🚨 *Ошибка вывода!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Ошибка при создании чека ({e})")
        await bot.send_message(CHANNEL_ID, log_message)
        return

    # Получаем ссылку на чек
    check_str = str(check)
    pattern = r"bot_check_url='([^']+)'"
    match = re.search(pattern, check_str)
    link = match.group(1) if match else "Не удалось найти ссылку"

    # Отправляем чек пользователю
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Получить", url=link))
    response_text = (
        "✅ Чек успешно создан!\n"
        f"💰 Сумма: {amount:.2f} USDT\n"
        f"🆔 Чек ID: {check.check_id}\n"
    )
    await callback.message.answer(response_text, reply_markup=kb.as_markup())

    # Логируем успешный вывод в канал
    log_message = (f"✅ *Вывод успешно создан!*\n"
                   f"👤 Игрок: @{username}\n"
                   f"💰 Сумма: {amount:.2f} USDT\n"
                   f"🔗 [Ссылка на чек]({link})")
    await bot.send_message(CHANNEL_ID, log_message)

    # Удаляем сообщение через 15 секунд
    await asyncio.sleep(15)
    await callback.message.delete()



@router.message(WithdrawStates.waiting_for_amount)
async def process_manual_withdraw(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    username = message.from_user.username or f"ID: {telegram_id}"  # Берем username или ID

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

        # Логируем попытку вывода в канал
        channel_id = -1002453573888
        log_message = (f"🚨 *Попытка вывода отклонена!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Недостаточно средств (Баланс: {balance:.2f} USDT)")
        await message.bot.send_message(channel_id, log_message)
        return

    # Обновляем баланс
    new_balance = balance - amount
    cursor.execute("UPDATE user SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

    try:
        check = await crypto.create_check(asset='USDT', amount=amount)
    except Exception as e:
        await message.answer("Ошибка при создании чека")
        await state.clear()

        # Логируем ошибку создания чека
        channel_id = -1002453573888
        log_message = (f"🚨 *Ошибка вывода!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Ошибка при создании чека")
        await message.bot.send_message(channel_id, log_message)
        return

    # Извлекаем ссылку на чек
    check_str = str(check)
    pattern = r"bot_check_url='([^']+)'"
    match = re.search(pattern, check_str)

    if match:
        link = match.group(1)
    else:
        link = "Не удалось найти ссылку"

    # Клавиатура с кнопкой "Получить"
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text='Получить', url=link))

    response_text = (
        "✅ Чек успешно создан!\n"
        f"💰 Сумма: {amount:.2f} USDT\n"
        f"🆔 Чек ID: {check.check_id}\n"
    )

    await message.answer(response_text, reply_markup=kb.as_markup())

    # Логируем успешный вывод в канал
    channel_id = -1002453573888
    log_message = (f"✅ *Вывод успешно создан!*\n"
                   f"👤 Игрок: @{username}\n"
                   f"💰 Сумма: {amount:.2f} USDT\n"
                   f"🔗 [Ссылка на чек]({link})")
    await message.bot.send_message(channel_id, log_message)

    # Очищаем состояние и удаляем сообщение через 15 секунд
    await state.clear()
    await asyncio.sleep(15)
    await message.delete()
