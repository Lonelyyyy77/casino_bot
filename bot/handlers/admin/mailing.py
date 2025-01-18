import sqlite3

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.admin.states import MailingState
from ...database import DB_NAME

router = Router()


@router.callback_query(lambda c: c.data == 'mailing')
async def start_mailing(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(MailingState.enter_text)
    await callback.message.edit_text('Введите текст для рассылки:')


@router.message(MailingState.enter_text)
async def input_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    skip_button = InlineKeyboardBuilder()
    skip_button.add(InlineKeyboardButton(text="Пропустить", callback_data="skip_media"))
    await state.set_state(MailingState.add_media)
    await message.answer('Отправьте медиа (изображение/видео/гиф) или нажмите "Пропустить":',
                         reply_markup=skip_button.as_markup())


@router.message(MailingState.add_media, F.content_type.in_(['photo', 'video', 'animation']))
async def input_media(message: types.Message, state: FSMContext):
    media_id = None
    media_type = None

    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        media_id = message.animation.file_id
        media_type = "animation"

    await state.update_data(media=media_id, media_type=media_type)
    await state.set_state(MailingState.confirm)
    await show_preview(message, state)


@router.callback_query(MailingState.add_media, lambda c: c.data == 'skip_media')
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(MailingState.confirm)
    await show_preview(callback.message, state)


@router.callback_query(lambda c: c.data == "add_reward_button")
async def add_reward_button(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(MailingState.enter_reward_amount)
    await callback.message.answer("Введите сумму вознаграждения (в JPC):")


@router.message(MailingState.enter_reward_amount)
async def set_reward_amount(message: types.Message, state: FSMContext):
    try:
        reward_amount = float(message.text.replace(",", "."))
        if reward_amount <= 0:
            raise ValueError("Сумма должна быть положительным числом.")
        await state.update_data(reward_amount=reward_amount)
        await state.set_state(MailingState.enter_reward_uses)
        await message.answer("Введите количество активаций кнопки:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число (например, 1.5).")



@router.message(MailingState.enter_reward_uses)
async def set_reward_uses(message: types.Message, state: FSMContext):
    try:
        reward_uses = int(message.text)
        if reward_uses <= 0:
            raise ValueError("Количество активаций должно быть положительным числом.")
        await state.update_data(reward_uses=reward_uses)
        await state.set_state(MailingState.confirm)
        await message.answer(f"Кнопка вознаграждения настроена: {reward_uses} активаций.")
        await show_preview(message, state)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число.")


async def show_preview(message_or_callback, state: FSMContext):
    data = await state.get_data()
    text = data.get('text', 'Текст отсутствует.')
    media_id = data.get('media')
    media_type = data.get('media_type')
    reward_amount = data.get('reward_amount')

    confirm_buttons = InlineKeyboardBuilder()
    confirm_buttons.add(InlineKeyboardButton(text="Отослать", callback_data="send_mailing"))
    confirm_buttons.add(InlineKeyboardButton(text="Отменить", callback_data="cancel_mailing"))
    confirm_buttons.row(
        InlineKeyboardButton(text="Добавить кнопку с вознаграждением", callback_data="add_reward_button"))

    if media_id:
        if media_type == "photo":
            await message_or_callback.answer_photo(photo=media_id, caption=text,
                                                   reply_markup=confirm_buttons.as_markup())
        elif media_type == "video":
            await message_or_callback.answer_video(video=media_id, caption=text,
                                                   reply_markup=confirm_buttons.as_markup())
        elif media_type == "animation":
            await message_or_callback.answer_animation(animation=media_id, caption=text,
                                                       reply_markup=confirm_buttons.as_markup())
    else:
        await message_or_callback.answer(text, reply_markup=confirm_buttons.as_markup())

    if reward_amount:
        await message_or_callback.answer(f"Добавлена кнопка с вознаграждением: {reward_amount} JPC.")


@router.callback_query(MailingState.confirm, lambda c: c.data == 'send_mailing')
async def send_mailing(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get('text', 'Текст отсутствует.')
    media_id = data.get('media')
    media_type = data.get('media_type')
    reward_amount = data.get('reward_amount')
    reward_uses = data.get('reward_uses')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if reward_amount and reward_uses:
        cursor.execute(
            "INSERT INTO reward_buttons (amount, remaining_uses) VALUES (?, ?)",
            (reward_amount, reward_uses)
        )
        button_id = cursor.lastrowid
        conn.commit()

    cursor.execute("SELECT telegram_id FROM user")
    users = cursor.fetchall()

    failed = []

    for user in users:
        telegram_id = user[0]
        try:
            if reward_amount and reward_uses:
                reward_button = InlineKeyboardBuilder()
                reward_button.add(
                    InlineKeyboardButton(
                        text=f"Забрать {reward_amount} JPC, осталось {reward_uses}",
                        callback_data=f"claim_reward_{button_id}"
                    )
                )
                reply_markup = reward_button.as_markup()
            else:
                reply_markup = None

            if media_id:
                if media_type == "photo":
                    await callback.bot.send_photo(chat_id=telegram_id, photo=media_id, caption=text,
                                                  reply_markup=reply_markup)
                elif media_type == "video":
                    await callback.bot.send_video(chat_id=telegram_id, video=media_id, caption=text,
                                                  reply_markup=reply_markup)
                elif media_type == "animation":
                    await callback.bot.send_animation(chat_id=telegram_id, animation=media_id, caption=text,
                                                      reply_markup=reply_markup)
            else:
                await callback.bot.send_message(chat_id=telegram_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            failed.append(telegram_id)
            print(f"Не удалось отправить сообщение пользователю {telegram_id}: {e}")

    conn.close()

    if failed:
        await callback.message.answer(
            f"Рассылка завершена. Не удалось отправить сообщения {len(failed)} пользователям."
        )
    else:
        await callback.message.answer("Рассылка успешно завершена всем пользователям.")

    await state.clear()



@router.callback_query(MailingState.confirm, lambda c: c.data == 'cancel_mailing')
async def cancel_mailing(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Рассылка отменена.")
    await state.clear()
