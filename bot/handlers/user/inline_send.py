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
    1) Парсим "10 @User [коммент]" из query.query.
    2) Отправляем получателю ЛС (с кнопкой "Получить") прямо из этого хендлера.
    3) Возвращаем карточку в инлайн‑меню.

    ВНИМАНИЕ: Этот подход может вызывать спам, т.к. inline_query
    вызывается при КАЖДОМ вводе символа, и юзер может НЕ выбрать этот результат.
    """
    text = query.query.strip()
    if not text:
        await query.answer([], cache_time=1)
        return

    parts = text.split(maxsplit=2)
    amount_str = parts[0] if len(parts) > 0 else "0"
    recipient_mention = parts[1] if len(parts) > 1 else "@???"
    comment = parts[2] if len(parts) > 2 else ""

    # Попробуем определить сумму, получателя и отправителя
    try:
        amount = int(amount_str)
    except ValueError:
        amount = 0

    sender_id = query.from_user.id
    sender_username = query.from_user.username or "UnknownUser"

    # Обрежем "@" у получателя
    recipient_username = recipient_mention.lstrip("@")
    recipient_data = get_user_by_username(recipient_username) if recipient_username else None

    # Создаём текст, который попадёт в чат при выборе карточки
    title = f"Отправить {amount} JPC"
    description = f"Получатель: {recipient_mention}, Комментарий: {comment}"
    message_text = f"Попытка перевода {amount} JPC => {recipient_mention}\n{comment}"

    # Формируем саму карточку для инлайн‑меню
    result = InlineQueryResultArticle(
        id="transfer_coins",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=message_text
        )
    )

    # Отправляем уведомление получателю (с кнопкой "Получить")
    # ПРЕДУПРЕЖДЕНИЕ: это вызовется при КАЖДОМ inline_query — потенциальный СПАМ
    if recipient_data and amount > 0:
        recipient_tg_id = recipient_data["telegram_id"]

        callback_data = f"inline_trade:{sender_id}:{recipient_tg_id}:{amount}:{comment}"
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="Получить", callback_data=callback_data))

        try:
            await bot.send_message(
                recipient_tg_id,
                (
                    f"[IN INLINE_QUERY] Вам хотят отправить {amount} JPC от @{sender_username}\n"
                    f"Комментарий: {comment}\n\n"
                    "Нажмите кнопку, чтобы получить."
                ),
                reply_markup=kb
            )
            logging.info("Уведомление отправлено получателю (в inline_query).")
        except Exception as e:
            logging.warning(f"Не удалось отправить ЛС получателю: {e}")

    # Возвращаем одну карточку
    await query.answer([result], cache_time=1)


@router.callback_query(lambda c: c.data.startswith("inline_trade:"))
async def callback_handler(call: types.CallbackQuery):
    data = call.data or ""
    if not data.startswith("inline_trade:"):
        await call.answer("Неизвестный колбэк", show_alert=False)
        return

    parts = data.split(":", 4)
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

    # Проверяем баланс у отправителя
    sender_balance = get_user_balance(sender_id)
    if sender_balance < amount:
        await call.answer("У отправителя уже недостаточно средств!", show_alert=True)
        return

    # Выполняем перевод
    update_user_balance(sender_id, -amount)
    update_user_balance(recipient_id, amount)

    await call.answer("Монеты зачислены!", show_alert=True)
    await call.message.edit_text(
        f"Вы получили {amount} JPC.\nКомментарий: {comment}"
    )
    # Уведомим отправителя
    try:
        await bot.send_message(sender_id, f"Получатель подтвердил перевод {amount} JPC.")
    except:
        pass
