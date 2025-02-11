import sqlite3

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from bot.database import DB_NAME
from bot.states.admin.states import PromoState

router = Router()


@router.callback_query(lambda c: c.data == "create_promo")
async def start_promo_creation(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название промокода:")
    await state.set_state(PromoState.waiting_for_code)


@router.message(PromoState.waiting_for_code)
async def get_promo_code(message: types.Message, state: FSMContext):
    promo_code = message.text.strip().upper()

    if len(promo_code) < 3 or len(promo_code) > 20:
        await message.answer("Ошибка! Название промокода должно быть от 3 до 20 символов.")
        return

    await state.update_data(promo_code=promo_code)
    await message.answer("Введите сумму бонуса (в USDT):")
    await state.set_state(PromoState.waiting_for_amount)


@router.message(PromoState.waiting_for_amount)
async def get_promo_amount(message: types.Message, state: FSMContext):
    try:
        bonus_amount = float(message.text.replace(',', '.'))
        if bonus_amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Ошибка! Введите корректное число (например: 5, 10, 20 USDT).")
        return

    await state.update_data(bonus_amount=bonus_amount)
    await message.answer("Введите максимальное количество активаций:")
    await state.set_state(PromoState.waiting_for_activations)


@router.message(PromoState.waiting_for_activations)
async def get_promo_activations(message: types.Message, state: FSMContext):
    try:
        max_activations = int(message.text)
        if max_activations < 1:
            raise ValueError
    except ValueError:
        await message.answer("Ошибка! Введите целое число больше 0.")
        return

    data = await state.get_data()
    promo_code = data["promo_code"]
    bonus_amount = data["bonus_amount"]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO promo_codes (code, bonus_amount, max_activations) VALUES (?, ?, ?)",
            (promo_code, bonus_amount, max_activations),
        )
        conn.commit()
        await message.answer(f"✅ Промокод <b>{promo_code}</b> создан!\n"
                             f"💰 Бонус: {bonus_amount:.2f} USDT\n"
                             f"🔄 Активаций: {max_activations}",
                             parse_mode="HTML")
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Промокод с таким названием уже существует! Попробуйте другое имя.")

    conn.close()
    await state.clear()
