import sqlite3

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.user.user import get_menu_image
from bot.states.user.user import TransferState

router = Router()


@router.callback_query(lambda c: c.data == "transfer_balance")
async def start_transfer(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransferState.enter_username)

    transfer_image = get_menu_image("transfer")

    text = (
        "Введите ник пользователя, которому нужно отправить JPC\n\n"
        "Пожалуйста, вводите имя пользователя верно, иначе средства пропадут и возвращены не будут.\n"
        "Пример: @Durov"
    )

    if transfer_image:
        if isinstance(transfer_image, str):
            photo = transfer_image
        else:
            photo = InputFile(transfer_image)

        try:
            media = InputMediaPhoto(media=photo, caption=text)
            await callback.message.edit_media(media=media)
        except:
            await callback.message.answer_photo(photo=photo, caption=text)
    else:
        await callback.message.answer(text)


@router.message(TransferState.enter_username)
async def enter_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        await message.answer("Ник должен начинаться с символа '@'. Попробуйте снова.")
        return

    await state.update_data(target_username=username)
    await state.set_state(TransferState.enter_amount)

    transfer_image = get_menu_image("transfer")

    text = (
        "Введите сумму, которую нужно передать пользователю\n"
        "Если вы хотите передать сумму с копейками, обозначайте их через точку.\n"
        "Пример: 7.75"
    )

    if transfer_image:
        if isinstance(transfer_image, str):
            photo = transfer_image
        else:
            photo = InputFile(transfer_image)

        await message.answer_photo(photo=photo, caption=text)
    else:
        await message.answer(text)


@router.message(TransferState.enter_amount)
async def enter_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом.")
    except ValueError:
        await message.answer("Введите корректную сумму. Пример: 7.75")
        return

    user_data = await state.get_data()
    target_username = user_data.get("target_username")
    await state.update_data(amount=amount)

    await state.set_state(TransferState.confirm_transfer)

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="💸 Передать", callback_data="confirm_transfer"))
    kb.add(InlineKeyboardButton(text="❌ Отмена ❌", callback_data="cancel_transfer"))

    transfer_image = get_menu_image("transfer")

    text = f"Вы собираетесь передать {target_username} {amount:.2f} JPC.\n\nПодтвердите действие:"

    if transfer_image:
        if isinstance(transfer_image, str):
            photo = transfer_image
        else:
            photo = InputFile(transfer_image)

        await message.answer_photo(photo=photo, caption=text, reply_markup=kb.as_markup())
    else:
        await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data == "confirm_transfer", TransferState.confirm_transfer)
async def confirm_transfer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sender_id = callback.from_user.id
    target_username = data.get("target_username")
    amount = data.get("amount")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, telegram_id FROM user WHERE username = ?", (target_username.strip("@"),))
    target_user = cursor.fetchone()

    if not target_user:
        await callback.answer("Пользователь с таким ником не найден.", show_alert=True)
        conn.close()
        return

    target_user_id, target_user_telegram_id = target_user

    cursor.execute("SELECT balance FROM user WHERE telegram_id = ?", (sender_id,))
    sender_balance = cursor.fetchone()

    if not sender_balance or sender_balance[0] < amount:
        await callback.answer("Недостаточно средств для выполнения перевода.", show_alert=True)
        conn.close()
        return

    cursor.execute("UPDATE user SET balance = balance - ? WHERE telegram_id = ?", (amount, sender_id))
    cursor.execute("UPDATE user SET balance = balance + ? WHERE id = ?", (amount, target_user_id))
    conn.commit()
    conn.close()

    transfer_image = get_menu_image("transfer")

    text = f"{amount:.2f} JPC были успешно переданы пользователю {target_username}"

    if transfer_image:
        if isinstance(transfer_image, str):
            photo = transfer_image
        else:
            photo = InputFile(transfer_image)

        await callback.message.answer_photo(photo=photo, caption=text)
    else:
        await callback.message.answer(text)

    try:
        await callback.bot.send_message(
            target_user_telegram_id,
            f"💸 Вам пришли {amount:.2f} JPC от @{callback.from_user.username}"
        )
    except:
        pass

    await state.clear()


@router.callback_query(lambda c: c.data == "cancel_transfer", TransferState.confirm_transfer)
async def cancel_transfer(callback: types.CallbackQuery, state: FSMContext):
    transfer_image = get_menu_image("transfer")

    text = "❌ Передача отменена."

    if transfer_image:
        if isinstance(transfer_image, str):
            photo = transfer_image
        else:
            photo = InputFile(transfer_image)

        await callback.message.answer_photo(photo=photo, caption=text)
    else:
        await callback.message.answer(text)

    await state.clear()

