import asyncio
import logging
import sqlite3
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice, InlineKeyboardButton, PreCheckoutQuery, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiocryptopay import AioCryptoPay, Networks
from aiohttp import web
from aiocryptopay.models.update import Update

from bot.database import DB_NAME
from bot.database.user.user import update_user_balance
from bot.start_bot import bot, CRYPTO_TOKEN
from bot.states.user.user import PaymentState

crypto = AioCryptoPay(
    token=CRYPTO_TOKEN,
    network=Networks.TEST_NET  # TEST_NET для тестирования
)
web_app = web.Application()

CURRENCY_USD = 'USD'
CURRENCY = 'XTR'
STARS_RATE = 0.013
MIN_JPC = 0.1

db_lock = asyncio.Lock()

router = Router()


def choose_amount_payment_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="2 JPC (2$)", callback_data="jpc_2"))
    builder.row(InlineKeyboardButton(text="5 JPC (5$)", callback_data="jpc_5"))
    builder.row(InlineKeyboardButton(text="10 JPC (10$)", callback_data="jpc_10"))
    return builder.as_markup()


def payment_kb():
    builder = InlineKeyboardBuilder()
    pay_button = InlineKeyboardButton(text="⭐️ PAY NOW ⭐️", pay=True)
    builder.row(pay_button)
    return builder.as_markup()


def process_deposit(user_id, amount):
    """
    Функция для начисления суммы на баланс и обработки реферального бонуса.
    Здесь в качестве user_id можно использовать внутренний id из БД.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("UPDATE user SET balance = balance + ? WHERE id = ?", (amount, user_id))
    cursor.execute("SELECT referrer_id FROM user WHERE id = ?", (user_id,))
    referrer_row = cursor.fetchone()

    if referrer_row and referrer_row[0]:
        referrer_id = referrer_row[0]
        cursor.execute("SELECT referral_percent FROM user WHERE id = ?", (referrer_id,))
        referral_percent_row = cursor.fetchone()
        referral_percent = referral_percent_row[0] if referral_percent_row and referral_percent_row[0] else 10

        referral_reward = amount * (referral_percent / 100)

        cursor.execute(
            "UPDATE user SET balance = balance + ?, referral_earnings = referral_earnings + ? WHERE id = ?",
            (referral_reward, referral_reward, referrer_id)
        )
        cursor.execute("SELECT telegram_id FROM user WHERE id = ?", (referrer_id,))
        referrer_telegram_row = cursor.fetchone()
        conn.commit()
        conn.close()
        return referrer_telegram_row[0] if referrer_telegram_row else None, referral_reward

    conn.commit()
    conn.close()
    return None, None


async def notify_referrer_about_referral(bot, referrer_telegram_id, referral_name, deposit_amount, referral_reward):
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
    await callback.message.edit_text(
        "Выберите, сколько JPC вы хотите пополнить:",
        reply_markup=choose_amount_payment_kb()
    )


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

        stars_needed = jpc_amount / STARS_RATE  # вычисляем эквивалент в "звёздах"
        await state.update_data(jpc_amount=jpc_amount, stars_needed=stars_needed)
        await message.answer(
            f"Вы выбрали пополнение на {jpc_amount} JPC ({jpc_amount}$). Это эквивалентно {stars_needed:.2f} звёзд. Подтвердите, пожалуйста.",
            reply_markup=InlineKeyboardBuilder().add(
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm_payment")
            ).as_markup()
        )
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество JPC (число). Попробуйте снова.")


@router.callback_query(lambda c: c.data.startswith('jpc_'))
async def handle_jpc_choice(callback: CallbackQuery, state: FSMContext):
    """
    Обработка выбора фиксированной суммы (2, 5, 10 и тестовая 0.1)
    """
    try:
        jpc_amount = float(callback.data.split('_')[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка определения суммы. Попробуйте ещё раз.", show_alert=True)
        return

    if jpc_amount < MIN_JPC:
        await callback.answer(f"Минимальная сумма пополнения: {MIN_JPC} JPC.", show_alert=True)
        return

    stars_needed = jpc_amount / STARS_RATE
    await state.update_data(jpc_amount=jpc_amount, stars_needed=stars_needed)

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Оплатить звездами (Telegram Pay)", callback_data="confirm_payment_stars"))
    kb.add(InlineKeyboardButton(text="Оплатить через Crypto Bot", callback_data="confirm_payment_crypto_bot"))

    await callback.message.answer(
        (
            f"Вы выбрали пополнение на {jpc_amount} JPC (это {jpc_amount}$).\n"
            f"Эквивалентно ~{stars_needed:.2f} звёзд.\n\n"
            "Выберите способ оплаты:"
        ),
        reply_markup=kb.as_markup()
    )


@router.callback_query(lambda c: c.data == "confirm_payment_crypto_bot")
async def handle_crypto_payment(callback: CallbackQuery, state: FSMContext):
    """
    Создаём инвойс через Crypto Bot, записываем invoice_id в БД,
    выдаём пользователю ссылку для оплаты и запускаем фоновую задачу для проверки платежа.
    """
    data = await state.get_data()
    jpc_amount = data.get('jpc_amount', 0)
    user_id = callback.from_user.id

    if float(jpc_amount) < 1 and str(jpc_amount) != '0.1':
        await callback.message.answer("Минимальная сумма для оплаты через USDT или TON — 1 USD.")
        return

    try:
        invoice = await crypto.create_invoice(
            amount=float(jpc_amount),
            fiat='USD',
            currency_type='fiat'
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка при создании инвойса: {e}")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO payments (invoice_id, user_id, jpc_amount, status)
        VALUES (?, ?, ?, ?)
        """,
        (invoice.invoice_id, user_id, jpc_amount, 'pending')
    )
    conn.commit()
    conn.close()

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Оплатить", url=invoice.bot_invoice_url))

    await callback.message.answer(
        f"Перейдите по ссылке и оплатите:\n{invoice.bot_invoice_url}\n\n"
        "После оплаты баланс будет пополнен автоматически.",
        reply_markup=kb.as_markup()
    )
    asyncio.create_task(check_payment_crypto_bot(user_id, invoice.invoice_id, jpc_amount))


@router.callback_query(lambda c: c.data == 'confirm_payment_stars')
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
    """
    Обработка успешного платежа через Telegram Pay.
    Начисление баланса и (при необходимости) реферальных бонусов.
    """
    user_data = await state.get_data()
    jpc_amount = user_data.get("jpc_amount")
    if not jpc_amount:
        await message.answer("Ошибка: не удалось определить сумму пополнения. Обратитесь к администрации.")
        return

    # Начисляем баланс пользователю (функция update_user_balance должна корректно обрабатывать идентификатор)
    update_user_balance(telegram_id=message.from_user.id, jpc_amount=jpc_amount)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, balance FROM user WHERE telegram_id = ?", (message.from_user.id,))
        user_row = cursor.fetchone()
        if not user_row:
            await message.answer("Пользователь не найден в базе данных.")
            return

        user_id, current_balance = user_row
        # Получаем данные реферала по внутреннему id
        cursor.execute("SELECT referrer_id, referral_percent FROM user WHERE id = ?", (user_id,))
        ref_data = cursor.fetchone()
        if not ref_data or not ref_data[0]:
            await message.answer(f"Платеж успешен! Вам начислено {jpc_amount} JPC. Спасибо за пополнение!")
            return

        referrer_id, referral_percent = ref_data
        cursor.execute("SELECT telegram_id FROM user WHERE id = ?", (referrer_id,))
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


async def check_payment_crypto_bot(user_id, invoice_id, jpc_amount):
    """
    Фоновая функция для опроса статуса инвойса.
    Если через 5 минут (60 циклов по 5 секунд) инвойс так и не будет оплачен,
    пользователю отправляется сообщение об истечении времени.
    """
    channel_id = -1002453573888  # Канал для логирования
    username = (await bot.get_chat(user_id)).username or f"ID: {user_id}"  # Получаем юзернейм

    for _ in range(60):
        await asyncio.sleep(5)
        try:
            async with db_lock:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM payments WHERE invoice_id=?", (invoice_id,))
                row = cursor.fetchone()
                conn.close()
            if row and row[0] == 'paid':
                return

            invoices = await crypto.get_invoices(invoice_ids=[invoice_id])
            if invoices and invoices[0].status == "paid":
                async with db_lock:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE payments SET status='paid' WHERE invoice_id=?", (invoice_id,))
                    conn.commit()
                    conn.close()

                update_user_balance(user_id, jpc_amount)

                # Проверяем наличие реферального бонуса
                async with db_lock:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT referrer_id, referral_percent
                        FROM user
                        WHERE telegram_id=?
                        """,
                        (user_id,)
                    )
                    ref_data = cursor.fetchone()
                    if ref_data and ref_data[0]:
                        referrer_id, referral_percent = ref_data
                        if not referral_percent:
                            referral_percent = 10
                        referral_reward = jpc_amount * (referral_percent / 100.0)
                        cursor.execute(
                            """
                            UPDATE user
                            SET balance = balance + ?,
                                referral_earnings = referral_earnings + ?
                            WHERE telegram_id = ?
                            """,
                            (referral_reward, referral_reward, referrer_id)
                        )
                        await bot.send_message(referrer_id,
                                               f'Ваш реферальный пользователь пополнил баланс, вы получили {referral_reward:.2f} JPC!')
                        conn.commit()
                    conn.close()

                await bot.send_message(user_id, f"✅ Ваш баланс пополнен на {jpc_amount} JPC!")
                log_message = (f"💰 *Пополнение баланса!*\n"
                               f"👤 Игрок: @{username}\n"
                               f"💳 Сумма: {jpc_amount:.2f} JPC\n"
                               f"🆔 Invoice ID: `{invoice_id}`\n"
                               f"✅ Статус: Успешно")

                await bot.send_message(channel_id, log_message)
                return

        except Exception as e:
            logging.error(f"Ошибка при проверке оплаты: {e}")

    # Если оплата не прошла за 5 минут
    await bot.send_message(user_id, "❌ Время оплаты истекло.")

    # Логируем неудачную оплату в канал
    log_message = (f"⚠️ *Оплата не завершена!*\n"
                   f"👤 Игрок: @{username}\n"
                   f"💳 Сумма: {jpc_amount:.2f} JPC\n"
                   f"🆔 Invoice ID: `{invoice_id}`\n"
                   f"❌ Статус: Время истекло")
    await bot.send_message(channel_id, log_message, parse_mode="Markdown")


@crypto.pay_handler()
async def invoice_paid(update: Update, app: web.Application):
    """
    Обработка уведомлений от крипто-платёжной системы.
    При получении статуса 'paid' обновляем БД, начисляем баланс и (при наличии) реферальный бонус.
    """
    logging.info(f"[CryptoBot] Получено уведомление: {update}")
    invoice = update.invoice
    if not invoice:
        logging.info("[CryptoBot] Invoice отсутствует в update")
        return

    if invoice.status != 'paid':
        logging.info(f"[CryptoBot] Invoice status is not 'paid': {invoice.status}")
        return

    invoice_id = invoice.invoice_id
    paid_amount = invoice.amount
    asset = invoice.asset
    logging.info(f"[CryptoBot] Invoice={invoice_id} оплачен. {paid_amount} {asset}.")

    async with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, jpc_amount, status
            FROM payments
            WHERE invoice_id=?
            """,
            (invoice_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            logging.info(f"[CryptoBot] Не нашли invoice_id={invoice_id} в таблице payments.")
            return

        user_id, jpc_amount, current_status = row
        if current_status == 'paid':
            conn.close()
            logging.info(f"[CryptoBot] Invoice={invoice_id} уже имеет статус 'paid'.")
            return

        cursor.execute(
            """
            UPDATE payments
            SET status='paid'
            WHERE invoice_id=?
            """,
            (invoice_id,)
        )
        conn.commit()
        conn.close()

    update_user_balance(user_id, jpc_amount)

    # Получаем имя пользователя
    user_data = await bot.get_chat(user_id)
    username = user_data.username or f"ID: {user_id}"

    channel_id = -1002453573888
    log_message = (f"💰 *Пополнение баланса!*\n"
                   f"👤 Игрок: @{username}\n"
                   f"💳 Сумма: {paid_amount} {asset}\n"
                   f"🆔 Invoice ID: `{invoice_id}`\n"
                   f"✅ Статус: Успешно")

    await bot.send_message(channel_id, log_message)

    # Отправляем уведомление пользователю
    await bot.send_message(user_id, f"✅ Ваш баланс пополнен на {paid_amount} {asset}!")

    logging.info(f"[CryptoBot] Пользователю {user_id} начислено {jpc_amount} JPC. invoice_id={invoice_id}")


web_app.add_routes([web.post('/crypto-secret-path', crypto.get_updates)])

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
