import datetime
from datetime import datetime
from time import strptime

from aiogram import Router, types
import sqlite3

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputFile

from bot.database import DB_NAME
from bot.database.user.user import get_menu_image
from bot.states.user.user import UserPromoState

router = Router()


@router.callback_query(lambda c: c.data == 'activate_promo')
async def request_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    promo_image = get_menu_image("promo")
    text = "🔑 Введите промокод:"

    if promo_image:
        media = InputMediaPhoto(media=promo_image, caption=text, parse_mode="HTML")
        sent_message = await callback.message.edit_media(media)
    else:
        sent_message = await callback.message.edit_text(text, parse_mode="HTML")

    await state.update_data(promo_message_id=sent_message.message_id)
    await state.set_state(UserPromoState.waiting_for_promo)


@router.message(UserPromoState.waiting_for_promo)
async def activate_promo(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    promo_code = message.text.strip().upper()

    await message.delete()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT bonus_amount, max_activations, used_activations, expiration_date FROM promo_codes WHERE code = ?",
        (promo_code,)
    )
    promo_data = cursor.fetchone()

    if not promo_data:
        await message.answer("⚠️ Промокод не найден! Попробуйте снова.")
        conn.close()
        return

    bonus_amount, max_activations, used_activations, expiration_date = promo_data

    # 🔥 Исправлено: теперь корректно преобразуем строку в datetime
    expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d %H:%M:%S')

    # Проверяем срок действия промокода
    if expiration_date < datetime.now():
        await message.answer("❌ Этот промокод истёк и больше не действует!")
        conn.close()
        return

    if used_activations >= max_activations:
        await message.answer("❌ Этот промокод уже исчерпан!")
        conn.close()
        return

    cursor.execute(
        "SELECT COUNT(*) FROM used_promos WHERE telegram_id = ? AND promo_code = ?",
        (telegram_id, promo_code)
    )
    already_used = cursor.fetchone()[0]

    if already_used > 0:
        await message.answer("⚠️ Вы уже использовали этот промокод!")
        conn.close()
        return

    cursor.execute("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", (bonus_amount, telegram_id))
    cursor.execute("INSERT INTO used_promos (telegram_id, promo_code) VALUES (?, ?)", (telegram_id, promo_code))
    cursor.execute("UPDATE promo_codes SET used_activations = used_activations + 1 WHERE code = ?", (promo_code,))

    conn.commit()
    conn.close()

    text = (
        f"🎉 Вы активировали промокод {promo_code}!\n"
        f"💰 Бонус: {bonus_amount:.2f} USDT\n"
        f"📅 Действует до: {expiration_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Новый баланс: обновлен"
    )

    promo_image = get_menu_image("promo")

    data = await state.get_data()
    promo_message_id = data.get("promo_message_id")

    if promo_image:
        if isinstance(promo_image, str):
            photo = promo_image
        else:
            photo = InputFile(promo_image)

        try:
            media = InputMediaPhoto(media=photo, caption=text)
            await message.bot.edit_message_media(media=media, chat_id=message.chat.id, message_id=promo_message_id)
        except TelegramBadRequest:
            await message.answer_photo(photo=photo, caption=text)
    else:
        try:
            await message.bot.edit_message_text(text, chat_id=message.chat.id, message_id=promo_message_id)
        except TelegramBadRequest:
            await message.answer(text)

    await state.clear()
