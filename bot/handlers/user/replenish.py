import sqlite3
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, InlineKeyboardButton, PreCheckoutQuery, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB_NAME
from database.user.user import update_user_balance
from states.user.user import PaymentState

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
    # builder.row(InlineKeyboardButton(text="Проверить уведомление", callback_data="11_pay"))
    # builder.row(InlineKeyboardButton(text="Другие суммы", callback_data="custom_jpc"))
    return builder.as_markup()


def payment_kb():
    builder = InlineKeyboardBuilder()

    pay_button = InlineKeyboardButton(text="⭐️ PAY NOW ⭐️", pay=True)
    builder.row(pay_button)

    return builder.as_markup()


def process_deposit(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE user SET balance = balance + ? WHERE id = ?", (amount, user_id))

    cursor.execute("SELECT referrer_id FROM user WHERE id = ?", (user_id,))
    referrer_id = cursor.fetchone()

    if referrer_id and referrer_id[0]:
        referrer_id = referrer_id[0]

        cursor.execute("SELECT referral_percent FROM user WHERE id = ?", (referrer_id,))
        referral_percent = cursor.fetchone()[0] or 10

        referral_reward = amount * (referral_percent / 100)

        cursor.execute("UPDATE user SET balance = balance + ?, referral_earnings = referral_earnings + ? WHERE id = ?",
                       (referral_reward, referral_reward, referrer_id))

        cursor.execute("SELECT telegram_id FROM user WHERE id = ?", (referrer_id,))
        referrer_telegram_id = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        return referrer_telegram_id, referral_reward

    conn.commit()
    conn.close()
    return None, None


async def notify_referrer_about_referral(
        bot,
        referrer_telegram_id,
        referral_name,
        deposit_amount,
        referral_reward
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT balance, referral_earnings FROM user WHERE telegram_id = ?",
            (referrer_telegram_id,)
        )
        row = cursor.fetchone()
        if not row:
            print(f"Не найден пользователь с telegram_id={referrer_telegram_id}. Не начисляем реферальный бонус.")
            return

        current_balance, current_ref_earnings = row

        if current_ref_earnings is None:
            current_ref_earnings = 0

        new_balance = current_balance + referral_reward
        new_ref_earnings = current_ref_earnings + referral_reward

        cursor.execute(
            """
            UPDATE user
            SET balance = ?,
                referral_earnings = ?
            WHERE telegram_id = ?
            """,
            (new_balance, new_ref_earnings, referrer_telegram_id)
        )
        conn.commit()

        message = (
            f"🐬 Ваш реферал {referral_name} пополнил баланс на {deposit_amount:.2f} JPC.\n"
            f"Вам начислено {referral_reward:.2f} JPC реферального вознаграждения!\n\n"
            f"Ваш текущий баланс: {new_balance:.2f} JPC.\n"
            f"Общая сумма заработка по рефералам: {new_ref_earnings:.2f} JPC."
        )
        await bot.send_message(referrer_telegram_id, message)

    except Exception as e:
        print(f"Ошибка при начислении реферального бонуса или отправке сообщения: {e}")
    finally:
        conn.close()


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
            InlineKeyboardButton(text="Подтвердить", callback_data="123")).as_markup()
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


@router.callback_query(lambda c: c.data == '123')
@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    jpc_amount = user_data.get("jpc_amount")

    if not jpc_amount:
        await message.answer("Ошибка: не удалось определить сумму пополнения. Обратитесь к администрации.")
        return

    update_user_balance(telegram_id=message.from_user.id, jpc_amount=jpc_amount)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, balance FROM user WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        user_row = cursor.fetchone()
        if not user_row:
            await message.answer("Пользователь не найден в базе данных.")
            return

        user_id, current_balance = user_row

        cursor.execute(
            "SELECT referrer_id, referral_percent FROM user WHERE id = ?",
            (user_id,)
        )
        ref_data = cursor.fetchone()
        if not ref_data or not ref_data[0]:
            await message.answer(f"Платеж успешен! Вам начислено {jpc_amount} JPC. Спасибо за пополнение!")
            return

        referrer_id, referral_percent = ref_data

        cursor.execute(
            "SELECT telegram_id FROM user WHERE telegram_id = ?",
            (referrer_id,)
        )
        referrer_telegram_data = cursor.fetchone()
        if not referrer_telegram_data:
            print(f"Проблема: Referrer {referrer_id} не найден в таблице user.")
            await message.answer(f"Платеж успешен! Вам начислено {jpc_amount} JPC. Спасибо за пополнение!")
            return

        referrer_telegram_id = referrer_telegram_data[0]

        referral_reward = jpc_amount * (referral_percent / 100.0)

        await notify_referrer_about_referral(
            bot=message.bot,
            referrer_telegram_id=referrer_telegram_id,
            referral_name=message.from_user.first_name,
            deposit_amount=jpc_amount,
            referral_reward=referral_reward
        )

        await message.answer(f"Платеж успешен! Вам начислено {jpc_amount} JPC. Спасибо за пополнение!")

    except Exception as e:
        print(f"Ошибка при обработке рефералов: {e}")
        await message.answer("Произошла ошибка во время обработки реферальных данных. Обратитесь к администрации.")

    finally:
        conn.close()

# @router.callback_query(lambda c: c.data == "check_referral")
# async def handle_check_referral(callback: types.CallbackQuery):
#     user_telegram_id = callback.from_user.id
#     user_name = callback.from_user.first_name
#
#     conn = sqlite3.connect(DB_NAME)
#     cursor = conn.cursor()
#
#     try:
#         cursor.execute(
#             "SELECT id, balance FROM user WHERE telegram_id = ?",
#             (user_telegram_id,)
#         )
#         user_data = cursor.fetchone()
#         if not user_data:
#             await callback.answer("Пользователь не найден в базе данных.", show_alert=True)
#             return
#
#         user_id, deposit_amount = user_data
#
#         cursor.execute(
#             "SELECT referrer_id, referral_percent FROM user WHERE id = ?",
#             (user_id,)
#         )
#         referrer_data = cursor.fetchone()
#
#         if not referrer_data or not referrer_data[0]:
#             await callback.answer("У вас нет реферера.", show_alert=True)
#             return
#
#         referrer_id, referral_percent = referrer_data
#
#         print(f"Referrer Data: {referrer_data}")
#
#         cursor.execute(
#             "SELECT telegram_id FROM user WHERE telegram_id = ?",
#             (referrer_id,)
#         )
#
#         referrer_telegram_id = cursor.fetchone()
#
#         if not referrer_telegram_id:
#             print(f"Проблема: Referrer ID {referrer_id} не найден в таблице user.")
#             await callback.answer("Не удалось найти Telegram ID реферера. Проверьте данные.", show_alert=True)
#             return
#
#         referrer_telegram_id = referrer_telegram_id[0]
#
#         referral_reward = deposit_amount * (referral_percent / 100)
#
#         await notify_referrer_about_referral(
#             bot=callback.bot,
#             referrer_telegram_id=referrer_telegram_id,
#             referral_name=user_name,
#             deposit_amount=deposit_amount,
#             referral_reward=referral_reward
#         )
#
#         await callback.answer("Оповещение успешно отправлено рефереру!")
#
#     except Exception as e:
#         await callback.answer(f"Ошибка: {e}", show_alert=True)
#
#     finally:
#         conn.close()
