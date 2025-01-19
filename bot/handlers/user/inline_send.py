import logging
from aiogram import Router, types, Bot
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from bot.database.user.user import (
    get_user_balance,
    update_user_balance,
    get_user_by_username
)
from bot.start_bot import bot  # ваш Bot объект

router = Router()


@router.inline_query()
async def inline_query_handler(query: types.InlineQuery):
    """
    Пользователь вводит: "10 @User [коммент]"
    Бот парсит:
      - amount (сумма)
      - @User (получатель)
      - [коммент] (необязательно)
    И возвращает одну инлайн-карточку.
    При выборе карточки в чат отправляется сообщение с кнопкой "Получить".
    """
    text = query.query.strip()
    if not text:
        await query.answer([], cache_time=1)
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        # Недостаточно данных (нет суммы или получателя)
        await query.answer([], cache_time=1)
        return

    amount_str = parts[0]
    recipient_mention = parts[1]  # например "@SomeUser"
    comment = parts[2] if len(parts) > 2 else ""

    # Парсим сумму
    try:
        amount = int(amount_str)
    except ValueError:
        amount = 0

    # Информация об отправителе (текущий пользователь)
    sender_id = query.from_user.id
    sender_username = query.from_user.username or "UnknownUser"

    # Обрезаем "@" у получателя
    recipient_username = recipient_mention.lstrip("@")
    recipient_data = get_user_by_username(recipient_username)

    # Тексты для карточки
    title = f"Отправить {amount} JPC"
    description = f"Получатель: {recipient_mention}, Комментарий: {comment}"
    message_text = f"Попытка перевода {amount} JPC => {recipient_mention}\n{comment}"

    if not recipient_data:
        # Если пользователя не нашли, в демо-режиме покажем заглушку
        title = "Ошибка: получатель не найден"
        description = "Проверьте @username"

    # Формируем callback_data. Храним ID получателя, чтобы точно знать, кто может "забрать" монеты.
    recipient_id = recipient_data["telegram_id"] if recipient_data else 0
    callback_data = f"inline_trade:{sender_id}:{recipient_id}:{amount}:{comment}"

    # Инлайн-клавиатура
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="Получить",
        callback_data=callback_data
    )
    kb = kb_builder.as_markup()

    # Создаём результат инлайн-запроса
    result = InlineQueryResultArticle(
        id="transfer_coins",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=message_text
        ),
        reply_markup=kb  # прикрепляем кнопку
    )

    # Возвращаем одну карточку
    await query.answer([result], cache_time=1)

@router.callback_query(lambda c: c.data.startswith("inline_trade:"))
async def callback_handler(call: types.CallbackQuery):
    """
    Формат callback_data: "inline_trade:<sender_id>:<recipient_id>:<amount>:<comment>"
    По нажатию на кнопку "Получить" проверяем:
      - Тот ли юзер нажал
      - Хватает ли баланса у отправителя
      - Выполняем перевод
      - Редактируем сообщение (кнопка исчезает)
      - Сообщаем отправителю, что перевод принят
    """
    data = call.data
    parts = data.split(":", 4)  # ["inline_trade", "123456", "222222", "10", "какой-то_коммент"]
    if len(parts) < 5:
        await call.answer("Неверные данные.", show_alert=True)
        return

    _, sender_str, recipient_str, amount_str, comment = parts

    # Парсим все числа
    try:
        sender_id = int(sender_str)
        recipient_id = int(recipient_str)
        amount = int(amount_str)
    except ValueError:
        await call.answer("Некорректные параметры.", show_alert=True)
        return

    # Проверяем, что нажал именно тот пользователь, которому предназначен перевод
    if call.from_user.id != recipient_id:
        await call.answer("Вы не тот пользователь, кому предназначен перевод!", show_alert=True)
        return

    # Проверяем баланс отправителя
    sender_balance = get_user_balance(sender_id)
    if sender_balance < amount:
        await call.answer("У отправителя уже недостаточно средств!", show_alert=True)
        return

    # Всё ок — выполняем перевод
    update_user_balance(sender_id, -amount)
    update_user_balance(recipient_id, amount)

    # Отвечаем пользователю (alert) и далее редактируем сообщение
    await call.answer("Монеты зачислены!", show_alert=True)

    # --- Убираем (или редактируем) сообщение, чтобы кнопку нельзя было нажать второй раз ---
    new_text = (
        f"@{call.from_user.username or call.from_user.id} "
        f"получил {amount} JPC.\nКомментарий: {comment}"
        f"Операция успешна ✅"
    )

    # Если call.message есть (обычное сообщение)
    if call.message:
        try:
            await call.message.edit_text(new_text)
        except Exception as e:
            logging.warning(f"Не удалось изменить сообщение: {e}")
    else:
        # Может быть inline_message_id, если это "инлайн-режим без сообщения"
        try:
            await bot.edit_message_text(
                inline_message_id=call.inline_message_id,
                text=new_text
            )
        except Exception as e:
            logging.warning(f"Не удалось изменить inline-сообщение: {e}")

    # Уведомим отправителя, что перевод принят
    try:
        await bot.send_message(sender_id, f"Получатель {recipient_id} подтвердил перевод {amount} JPC.")
    except Exception as e:
        logging.warning(f"Не удалось уведомить отправителя: {e}")