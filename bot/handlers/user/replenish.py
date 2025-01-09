import sqlite3
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, InlineKeyboardButton, PreCheckoutQuery, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.user.user import update_user_balance
from bot.states.user.user import PaymentState

CURRENCY_USD = 'USD'
CURRENCY = 'XTR'
STARS_RATE = 0.013
MIN_JPC = 2

router = Router()


def choose_amount_payment_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="2 JPC (2$)", callback_data="jpc_2"))
    builder.row(InlineKeyboardButton(text="5 JPC (5$)", callback_data="jpc_5"))
    builder.row(InlineKeyboardButton(text="10 JPC (10$)", callback_data="jpc_10"))
    # builder.row(InlineKeyboardButton(text="Другие суммы", callback_data="custom_jpc"))
    return builder.as_markup()


def payment_kb():
    builder = InlineKeyboardBuilder()

    pay_button = InlineKeyboardButton(text="⭐️ PAY NOW ⭐️", pay=True)
    builder.row(pay_button)

    return builder.as_markup()


@router.callback_query(lambda c: c.data == 'replenish')
async def replenish(callback: CallbackQuery):
    await callback.message.edit_text("Выберите, сколько JPC вы хотите пополнить:",
                                     reply_markup=choose_amount_payment_kb())


@router.callback_query(lambda c: c.data == "custom_jpc")
async def custom_jpc(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите количество JPC, которое вы хотите пополнить (минимум 2 JPC):")
    await state.set_state(PaymentState.waiting_for_jpc)


@router.message(PaymentState.waiting_for_jpc)
async def process_custom_jpc(message: types.Message, state: FSMContext):
    try:
        jpc_amount = int(message.text)

        if jpc_amount < 2:
            await message.answer("Минимум для пополнения - 2 JPC. Попробуйте снова.")
            return

        stars_needed = jpc_amount * 1 / STARS_RATE

        await state.update_data(jpc_amount=jpc_amount, stars_needed=stars_needed)

        await message.answer(
            f"Вы выбрали пополнение на {jpc_amount} JPC ({jpc_amount}$). Это эквивалентно {stars_needed:.2f} звёзд. Подтвердите, пожалуйста.",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm_payment")).as_markup()
        )

        await state.clear()

    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество JPC (число). Попробуйте снова.")


@router.callback_query(lambda c: c.data.startswith('jpc_'))
async def handle_jpc_choice(callback: CallbackQuery, state: FSMContext):
    jpc_amount = int(callback.data.split('_')[1])

    if jpc_amount < MIN_JPC:
        await callback.answer(f"Минимальная сумма пополнения {MIN_JPC} JPC.", show_alert=True)
        return

    stars_needed = jpc_amount * 1 / STARS_RATE

    await state.update_data(jpc_amount=jpc_amount, stars_needed=stars_needed)

    await callback.message.answer(
        f"Вы выбрали пополнение на {jpc_amount} JPC ({jpc_amount}$). Это эквивалентно {stars_needed:.2f} звёзд. Подтвердите, пожалуйста.",
        reply_markup=InlineKeyboardBuilder().add(
            InlineKeyboardButton(text="Подтвердить", callback_data="confirm_payment")).as_markup()
    )


@router.callback_query(lambda c: c.data == 'confirm_payment')
async def confirm_payment(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    user_data = await state.get_data()
    jpc_amount = user_data.get('jpc_amount')
    stars_needed = user_data.get('stars_needed')

    labeled_price = [LabeledPrice(label="Пополнение", amount=int(stars_needed))]

    await callback.message.answer_invoice(
        title=f"Оплата через Telegram для пополнения {jpc_amount} JPC",
        description=f"Оплата {jpc_amount} JPC на сумму {int(stars_needed)} звёзд",
        payload=f"payment_{jpc_amount}",
        provider_token="",
        currency=CURRENCY,
        prices=labeled_price,
        reply_markup=payment_kb(),
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    jpc_amount = user_data.get('jpc_amount')

    if not jpc_amount:
        await message.answer("Ошибка: не удалось определить сумму пополнения. Обратитесь к администрации.")
        return

    update_user_balance(telegram_id=message.from_user.id, jpc_amount=jpc_amount)

    await message.answer(f"Платеж успешен! Вам начислено {jpc_amount} JPC. Спасибо за пополнение!")
