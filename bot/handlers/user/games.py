import asyncio
import sqlite3

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pyexpat.errors import messages

from bot.database import DB_NAME

router = Router()

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()


@router.callback_query(lambda c: c.data == 'games')
async def games(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    cursor.execute("SELECT balance, current_bet, total_bets FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data_bet = cursor.fetchone()
    await callback.message.edit_text('Выберете игру:', reply_markup=get_game_keyboard(current_bet=user_data_bet[1]))


@router.callback_query(lambda c: c.data in ['bones_game', 'basketball_game', 'bowling_game'])
async def game_selected(callback: CallbackQuery):
    telegram_id = callback.from_user.id

    cursor.execute("SELECT balance, current_bet, total_bets FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.message.answer("Вы не зарегистрированы!")
        return

    balance, current_bet, total_bets = user_data

    if balance < current_bet:
        await callback.answer("У вас недостаточно средств для ставки!", show_alert=False)
        return

    cursor.execute("UPDATE user SET balance = balance - ?, total_bets = total_bets + ? WHERE telegram_id = ?",
                   (current_bet, current_bet, telegram_id))
    conn.commit()

    text = (f"Вы выбрали игру: {callback.data.replace('_', ' ').title()}\n"
            f"Текущая ставка: {current_bet} USDT\nВаш баланс: {balance - current_bet:.2f} USDT")

    if callback.data in ['bones_game', 'bowling_game']:
        kb = InlineKeyboardBuilder()
        kb.add(
            InlineKeyboardButton(text='Больше 3', callback_data=f"{callback.data}_over"),
            InlineKeyboardButton(text='Меньше или равно 3', callback_data=f"{callback.data}_under")
        )
        await callback.message.edit_text(f"{text}\nНа что ставите?", reply_markup=kb.as_markup())
        return

    elif callback.data == 'basketball_game':
        dice_message = await callback.message.answer_dice(emoji="🏀")
        await asyncio.sleep(4)
        result = dice_message.dice.value

        if result > 3:  # Победа
            winnings = calculate_winnings(current_bet)
            cursor.execute("""
                UPDATE user 
                SET balance = balance + ? 
                WHERE telegram_id = ?
            """, (winnings, telegram_id))
            conn.commit()
            await callback.answer(
                f"🏀 Отличный бросок! Вы набрали {result} очков! Победа!\n"
                f"Вы выиграли: {winnings:.2f} USDT\nВаш баланс: {balance - current_bet + winnings:.2f} USDT",
                show_alert=True
            )
        else:
            await callback.answer(
                f"🏀 Не повезло, всего {result} очка. Проигрыш!\nВаш баланс: {balance - current_bet:.2f} USDT",
                show_alert=True
            )


@router.callback_query(lambda c: c.data.endswith('_over') or c.data.endswith('_under'))
async def process_bet_choice(callback: CallbackQuery):
    await callback.message.delete()

    telegram_id = callback.from_user.id

    # Разделяем данные callback на части
    data_parts = callback.data.rsplit('_', maxsplit=1)  # Разделяем только на последние два элемента
    if len(data_parts) != 2:
        await callback.message.answer("Некорректные данные выбора ставки.")
        return

    game_choice, bet_type = data_parts  # Распаковываем последние две части

    cursor.execute("SELECT balance, current_bet FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.message.answer("Вы не зарегистрированы!")
        return

    balance, current_bet = user_data

    if game_choice == "bones_game":
        dice_emoji = "🎲"
    elif game_choice == "bowling_game":
        dice_emoji = "🎳"
    else:
        await callback.message.answer("Некорректная игра.")
        return

    dice_message = await callback.message.answer_dice(emoji=dice_emoji)
    await asyncio.sleep(5)
    result = dice_message.dice.value

    win_condition = (result > 3 and bet_type == "over") or (result <= 3 and bet_type == "under")

    if win_condition:  # Победа
        winnings = calculate_winnings(current_bet)
        cursor.execute("""
            UPDATE user 
            SET balance = balance + ? 
            WHERE telegram_id = ?
        """, (winnings, telegram_id))
        conn.commit()
        await callback.message.answer(
            f"{dice_emoji} Вы выбросили: {result}. Победа!\n"
            f"Вы выиграли: {winnings:.2f} USDT\nВаш баланс: {balance + winnings:.2f} USDT",
            reply_markup=get_game_keyboard(current_bet)
        )
    else:  # Проигрыш
        await callback.message.answer(
            f"{dice_emoji} Вы выбросили: {result}. Проигрыш!\nВаш баланс: {balance:.2f} USDT",
            reply_markup=get_game_keyboard(current_bet)
        )



def calculate_winnings(bet):
    cursor.execute("SELECT percentage FROM game_settings WHERE id = 1")
    settings = cursor.fetchone()
    percentage = settings[0] / 100 if settings else 0.1
    return bet + (bet * percentage)


@router.callback_query(lambda c: c.data in ['increase_bet', 'decrease_bet'])
async def change_bet(callback: CallbackQuery):
    telegram_id = callback.from_user.id

    cursor.execute("SELECT current_bet FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.answer("Вы не зарегистрированы!", show_alert=True)
        return

    current_bet = user_data[0]
    previous_bet = current_bet

    if callback.data == 'increase_bet':
        current_bet = min(current_bet * 2, 100)
    elif callback.data == 'decrease_bet':
        current_bet = max(current_bet / 2, 0.1)

    if previous_bet == current_bet:
        await callback.answer("Ставка уже минимальная/максимальная!", show_alert=False)
        return

    cursor.execute("UPDATE user SET current_bet = ? WHERE telegram_id = ?", (current_bet, telegram_id))
    conn.commit()

    kb = get_game_keyboard(current_bet)

    new_message = f"Выберите игру или измените ставку:\nТекущая ставка: {current_bet:.1f} USDT"
    await callback.message.edit_text(new_message, reply_markup=kb)


def get_game_keyboard(current_bet):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='🎲 Кости', callback_data='bones_game'))
    kb.row(InlineKeyboardButton(text='🏀 Баскетбол', callback_data='basketball_game'))
    kb.row(InlineKeyboardButton(text='🎳 Боулинг', callback_data='bowling_game'))
    kb.row(InlineKeyboardButton(text='⬆️', callback_data='increase_bet'))
    kb.add(
        InlineKeyboardButton(text=f'{current_bet:.1f} USDT', callback_data='current_bet'),
        InlineKeyboardButton(text='⬇️', callback_data='decrease_bet'),
    )
    kb.row(InlineKeyboardButton(text='🔙 Назад', callback_data='home'))
    return kb.as_markup()
