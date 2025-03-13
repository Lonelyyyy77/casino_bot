import asyncio
import re

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, InputMediaPhoto
import sqlite3

from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.user.user import get_menu_image
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

    conn.close()

    withdrawal_image = get_menu_image("withdraw")

    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="2$", callback_data="withdraw_2"),
        InlineKeyboardButton(text="5$", callback_data="withdraw_5"),
        InlineKeyboardButton(text="10$", callback_data="withdraw_10"),
        InlineKeyboardButton(text="Ввести сумму", callback_data="withdraw_manual")
    )

    text = f"💰 Ваш доступный баланс для вывода: {balance:.2f} USDT\n\nВыберите сумму для вывода:"

    if withdrawal_image:
        try:
            media = InputMediaPhoto(media=withdrawal_image, caption=text, parse_mode="HTML")
            await callback.message.edit_media(media=media, reply_markup=keyboard.as_markup())
        except TelegramBadRequest:
            await callback.message.answer_photo(photo=withdrawal_image, caption=text, reply_markup=keyboard.as_markup())
    else:
        # Если изображения нет, отправляем просто текст
        await callback.message.answer(text, reply_markup=keyboard.as_markup())


@router.callback_query(lambda c: c.data.startswith("withdraw_"))
async def fixed_withdraw_handler(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    username = callback.from_user.username or f"ID: {telegram_id}"

    data = callback.data
    amount_dict = {
        "withdraw_2": 2.0,
        "withdraw_5": 5.0,
        "withdraw_10": 10.0
    }

    amount = amount_dict.get(data)

    if data == "withdraw_manual":
        await callback.message.edit_text("Введите сумму для вывода (в USDT):")
        await state.set_state(WithdrawStates.waiting_for_amount)
        return
    elif amount is None:
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
    withdrawal_image = get_menu_image("withdraw")
    channel_id = -1002453573888  # ID канала логов

    if balance < amount:
        await callback.answer("❌ Недостаточно средств для вывода.", show_alert=True)
        conn.close()

        log_message = (f"🚨 *Попытка вывода отклонена!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Недостаточно средств (Баланс: {balance:.2f} USDT)")

        await send_log_with_image(callback.bot, channel_id, withdrawal_image, log_message)
        return

    new_balance = balance - amount
    cursor.execute("UPDATE user SET balance = ? WHERE telegram_id = ?", (new_balance, telegram_id))
    conn.commit()
    conn.close()

    try:
        check = await crypto.create_check(asset='USDT', amount=amount)
    except Exception as e:
        await callback.message.answer("Ошибка при создании чека")
        await state.clear()

        log_message = (f"🚨 *Ошибка вывода!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Ошибка при создании чека")

        await send_log_with_image(callback.bot, channel_id, withdrawal_image, log_message)
        return

    check_str = str(check)
    pattern = r"bot_check_url='([^']+)'"
    match = re.search(pattern, check_str)

    link = match.group(1) if match else "Не удалось найти ссылку"

    # Отправка чека пользователю
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Получить", url=link))

    response_text = (
        "✅ Чек успешно создан!\n"
        f"💰 Сумма: {amount:.2f} USDT\n"
        f"🆔 Чек ID: {check.check_id}\n"
    )
    await callback.message.answer(response_text, reply_markup=kb.as_markup())
    await state.clear()

    # Лог в канал
    log_message = (f"✅ *Вывод успешно создан!*\n"
                   f"👤 Игрок: @{username}\n"
                   f"💰 Сумма: {amount:.2f} USDT\n"
                   f"🔗 [Ссылка на чек]({link})")

    await send_log_with_image(callback.bot, channel_id, withdrawal_image, log_message)

    await asyncio.sleep(15)
    await callback.message.delete()


async def send_log_with_image(bot, channel_id, image, text):
    """Отправка логов с картинкой, если доступно"""
    try:
        if image:
            await bot.send_photo(channel_id, photo=image, caption=text)
        else:
            await bot.send_message(channel_id, text)
    except TelegramBadRequest:
        await bot.send_message(channel_id, text)


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

    withdrawal_image = get_menu_image("withdraw")
    channel_id = -1002453573888  # ID канала логов

    if balance < amount:
        await message.answer("❌ Недостаточно средств для вывода.")
        conn.close()
        await state.clear()

        log_message = (f"🚨 *Попытка вывода отклонена!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Недостаточно средств (Баланс: {balance:.2f} USDT)")

        try:
            await message.bot.send_photo(channel_id, photo=withdrawal_image, caption=log_message)
        except TelegramBadRequest:
            await message.bot.send_message(channel_id, log_message, parse_mode="Markdown")

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

        log_message = (f"🚨 *Ошибка вывода!*\n"
                       f"👤 Игрок: @{username}\n"
                       f"💰 Запрошено: {amount:.2f} USDT\n"
                       f"❌ Причина: Ошибка при создании чека")

        try:
            await message.bot.send_photo(channel_id, photo=withdrawal_image, caption=log_message)
        except TelegramBadRequest:
            await message.bot.send_message(channel_id, log_message)

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
        "✅ Чек успешно создан!\n"
        f"💰 Сумма: {amount:.2f} USDT\n"
        f"🆔 Чек ID: {check.check_id}\n"
    )

    await message.answer(response_text, reply_markup=kb.as_markup())

    log_message = (f"✅ *Вывод успешно создан!*\n"
                   f"👤 Игрок: @{username}\n"
                   f"💰 Сумма: {amount:.2f} USDT\n"
                   f"🔗 [Ссылка на чек]({link})")

    try:
        await message.bot.send_photo(channel_id, photo=withdrawal_image, caption=log_message)
    except TelegramBadRequest:
        await message.bot.send_message(channel_id, log_message)

    await state.clear()
    await asyncio.sleep(15)
    await message.delete()