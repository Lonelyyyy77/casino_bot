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
        await query.answer([], cache_time=1)
        return

    amount_str = parts[0]
    recipient_mention = parts[1]
    comment = parts[2] if len(parts) > 2 else ""

    try:
        amount = int(amount_str)
    except ValueError:
        amount = 0

    sender_id = query.from_user.id
    sender_username = query.from_user.username or "UnknownUser"

    recipient_username = recipient_mention.lstrip("@")
    recipient_data = get_user_by_username(recipient_username)

    title = f"Отправить {amount} JPC"
    description = f"Получатель: {recipient_mention}, Комментарий: {comment}"
    message_text = f"Попытка перевода {amount} JPC => {recipient_mention}\n{comment}"

    if not recipient_data:
        title = "Ошибка: получатель не найден"
        description = "Проверьте @username"

    recipient_id = recipient_data["telegram_id"] if recipient_data else 0
    callback_data = f"inline_trade:{sender_id}:{recipient_id}:{amount}:{comment}"

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text="Получить",
        callback_data=callback_data
    )
    kb = kb_builder.as_markup()

    result = InlineQueryResultArticle(
        id="transfer_coins",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=message_text
        ),
        reply_markup=kb
    )

    await query.answer([result], cache_time=1)


@router.callback_query(lambda c: c.data.startswith("inline_trade:"))
async def callback_handler(call: types.CallbackQuery):
    data = call.data
    parts = data.split(":", 4)  # ["inline_trade", "123456", "222222", "10", "какой-то_коммент"]
    if len(parts) < 5:
        await call.answer("Неверные данные.", show_alert=True)
        return

    _, sender_str, recipient_str, amount_str, comment = parts

    try:
        sender_id = int(sender_str)
        recipient_id = int(recipient_str)
        amount = int(amount_str)
    except ValueError:
        await call.answer("Некорректные параметры.", show_alert=True)
        return

    if call.from_user.id != recipient_id:
        await call.answer("Вы не тот пользователь, кому предназначен перевод!", show_alert=True)
        return

    sender_balance = get_user_balance(sender_id)
    if sender_balance < amount:
        await call.answer("У отправителя уже недостаточно средств!", show_alert=True)
        return

    update_user_balance(sender_id, -amount)
    update_user_balance(recipient_id, amount)

    await call.answer("Монеты зачислены!", show_alert=True)

    try:
        sender_chat = await bot.get_chat(sender_id)
        sender_username = sender_chat.username or sender_chat.full_name or str(sender_id)
    except Exception:
        sender_username = str(sender_id)

    await bot.send_message(
        recipient_id,
        f"Вам было зачислено {amount} JPC от @{sender_username}."
    )

    new_text = (
        f"@{call.from_user.username or call.from_user.id} получил {amount} JPC.\n"
        f"Комментарий: {comment}\n"
        "Операция успешна ✅"
    )

    if call.message:
        try:
            await call.message.edit_text(new_text)
        except Exception as e:
            logging.warning(f"Не удалось изменить сообщение: {e}")
    else:
        try:
            await bot.edit_message_text(inline_message_id=call.inline_message_id, text=new_text)
        except Exception as e:
            logging.warning(f"Не удалось изменить inline-сообщение: {e}")

    try:
        await bot.send_message(sender_id, f"Получатель {recipient_id} подтвердил перевод {amount} JPC.")
    except Exception as e:
        logging.warning(f"Не удалось уведомить отправителя: {e}")
