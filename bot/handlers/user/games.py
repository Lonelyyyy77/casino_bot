import asyncio
import sqlite3

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.start_bot import bot
from bot.states.user.user import BetState

router = Router()

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()


@router.callback_query(lambda c: c.data == 'games')
async def games(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    cursor.execute("SELECT balance, current_bet, total_bets FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data_bet = cursor.fetchone()
    await callback.message.edit_text('Выберете игру:', reply_markup=get_game_keyboard(current_bet=user_data_bet[1]))


@router.callback_query(
    lambda c: c.data in ['bones_game', 'basketball_game', 'bowling_game', 'darts_game', 'football_game'])
async def game_selected(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    username = callback.from_user.username or f"ID: {telegram_id}"  # Берем username или ID

    cursor.execute("SELECT balance, current_bet, total_bets FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.message.answer("Вы не зарегистрированы!")
        return

    balance, current_bet, total_bets = user_data

    if balance < current_bet:
        await callback.answer("У вас недостаточно средств для ставки!", show_alert=False)
        return

    channel_id = -1002311474812
    game_name_map = {
        "bones_game": "🎲 Кости",
        "basketball_game": "🏀 Баскетбол",
        "bowling_game": "🎳 Боулинг",
        "darts_game": "🎯 Дартс",
        "football_game": "⚽ Футбол"
    }
    game_name = game_name_map.get(callback.data, "Неизвестная игра")

    # Вычитаем ставку у пользователя
    cursor.execute("UPDATE user SET balance = balance - ?, total_bets = total_bets + ? WHERE telegram_id = ?",
                   (current_bet, current_bet, telegram_id))
    conn.commit()

    # Отправляем стикер игры
    emoji_map = {
        'basketball_game': '🏀',
        'football_game': '⚽'
    }
    dice_message = await callback.message.answer_dice(emoji=emoji_map[callback.data])
    await asyncio.sleep(4)
    result = dice_message.dice.value

    # Удаляем стикер после показа результата
    try:
        await dice_message.delete()
    except:
        pass

    # Определяем результат
    if callback.data == 'football_game':  # Футбол: 1-2 (мимо) | 3-6 (гол)
        if result >= 3:
            winnings = calculate_winnings(current_bet)
            cursor.execute("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", (winnings, telegram_id))
            conn.commit()
            result_message = f"⚽ Гол! Вы выиграли {winnings:.2f} USDT\nВаш баланс: {balance - current_bet + winnings:.2f} USDT"
            game_outcome = f"✅ Победа (+{winnings:.2f} USDT)"
        else:
            result_message = f"⚽ Мимо! Вы проиграли.\nВаш баланс: {balance - current_bet:.2f} USDT"
            game_outcome = "❌ Проигрыш"
    else:  # Баскетбол: обычные правила (выше 3 - победа)
        if result > 3:
            winnings = calculate_winnings(current_bet)
            cursor.execute("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", (winnings, telegram_id))
            conn.commit()
            result_message = f"🏀 Отличный бросок! Вы выиграли {winnings:.2f} USDT\nВаш баланс: {balance - current_bet + winnings:.2f} USDT"
            game_outcome = f"✅ Победа (+{winnings:.2f} USDT)"
        else:
            result_message = f"🏀 Неудачный бросок. Вы проиграли.\nВаш баланс: {balance - current_bet:.2f} USDT"
            game_outcome = "❌ Проигрыш"

    # Логируем результат игры в канал
    log_message = (f"🎰 Игра завершена!\n"
                   f"👤 Игрок: @{username}\n"
                   f"🎮 Игра: {game_name}\n"
                   f"💰 Ставка: {current_bet:.2f} USDT\n"
                   f"🎲 Выпало: {result}\n"
                   f"🏆 Итог: {game_outcome}")

    await bot.send_message(channel_id, log_message)

    # Показываем результат и возвращаем клавиатуру с играми
    await callback.answer(result_message, show_alert=True)
    updated_user_data = cursor.execute("SELECT balance, current_bet FROM user WHERE telegram_id = ?",
                                       (telegram_id,)).fetchone()
    updated_balance, updated_bet = updated_user_data
    await callback.message.answer("Вы вернулись в меню!", reply_markup=get_game_keyboard(updated_bet))


@router.callback_query(lambda c: c.data in ['darts_red', 'darts_white'])
async def darts_result(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    username = callback.from_user.username or f"ID: {telegram_id}"  # Берем username или ID
    user_choice = callback.data.split('_')[1]  # red / white

    cursor.execute("SELECT balance, current_bet FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()
    if not user_data:
        await callback.message.answer("Вы не зарегистрированы!")
        return

    balance, current_bet = user_data

    # Отправляем анимацию броска
    dice_message = await callback.message.answer_dice(emoji="🎯")
    await asyncio.sleep(4)
    result = dice_message.dice.value

    # Удаляем стикер с броском
    try:
        await dice_message.delete()
    except:
        pass  # Игнорируем ошибку, если сообщение уже удалено

    # Определяем, попал ли игрок в нужную зону
    if (user_choice == "red" and result in [1, 2, 3]) or (user_choice == "white" and result in [4, 5, 6]):
        winnings = calculate_winnings(current_bet)
        cursor.execute("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", (winnings, telegram_id))
        conn.commit()
        result_message = f"🎯 Точно в цель! Вы выбрали {user_choice} и выиграли {winnings:.2f} USDT\nВаш баланс: {balance - current_bet + winnings:.2f} USDT"
        game_outcome = f"✅ Победа (+{winnings:.2f} USDT)"
    else:
        result_message = f"🎯 Промах! Вы проиграли.\nВаш баланс: {balance - current_bet:.2f} USDT"
        game_outcome = "❌ Проигрыш"

    # Логируем результат игры в канал
    channel_id = -1002311474812
    log_message = (f"🎰 Игра завершена!\n"
                   f"👤 Игрок: @{username}\n"
                   f"🎯 Дартс\n"
                   f"🎨 Выбор: {'🔴 Красное' if user_choice == 'red' else '⚪ Белое'}\n"
                   f"💰 Ставка: {current_bet:.2f} USDT\n"
                   f"🎯 Выпало: {result}\n"
                   f"🏆 Итог: {game_outcome}")

    await bot.send_message(channel_id, log_message)

    # Показываем результат и возвращаем клавиатуру с играми
    await callback.answer(result_message, show_alert=True)
    updated_user_data = cursor.execute("SELECT balance, current_bet FROM user WHERE telegram_id = ?",
                                       (telegram_id,)).fetchone()
    updated_balance, updated_bet = updated_user_data
    await callback.message.answer("Вы вернулись в меню!", reply_markup=get_game_keyboard(updated_bet))


@router.callback_query(lambda c: c.data.endswith('_over') or c.data.endswith('_under'))
async def process_bet_choice(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    username = callback.from_user.username or f"ID: {telegram_id}"  # Берем username или ID

    data_parts = callback.data.rsplit('_', maxsplit=1)
    if len(data_parts) != 2:
        await callback.message.answer("Некорректные данные выбора ставки.")
        return

    game_choice, bet_type = data_parts

    cursor.execute("SELECT balance, current_bet FROM user WHERE telegram_id = ?", (telegram_id,))
    user_data = cursor.fetchone()

    if not user_data:
        await callback.message.answer("Вы не зарегистрированы!")
        return

    balance, current_bet = user_data

    game_emojis = {
        "bones_game": "🎲",
        "bowling_game": "🎳"
    }
    dice_emoji = game_emojis.get(game_choice)

    if not dice_emoji:
        await callback.message.answer("Некорректная игра.")
        return

    # Отправляем стикер броска
    dice_message = await callback.message.answer_dice(emoji=dice_emoji)
    await asyncio.sleep(5)
    result = dice_message.dice.value

    # Удаляем стикер
    try:
        await dice_message.delete()
    except:
        pass

    win_condition = (result > 3 and bet_type == "over") or (result <= 3 and bet_type == "under")

    if win_condition:  # Победа
        winnings = calculate_winnings(current_bet)
        cursor.execute("UPDATE user SET balance = balance + ? WHERE telegram_id = ?", (winnings, telegram_id))
        conn.commit()
        result_message = f"{dice_emoji} Вы выбросили: {result}. Победа!\nВы выиграли: {winnings:.2f} USDT\nВаш баланс: {balance + winnings:.2f} USDT"
        game_outcome = f"✅ Победа (+{winnings:.2f} USDT)"
    else:  # Проигрыш
        result_message = f"{dice_emoji} Вы выбросили: {result}. Проигрыш!\nВаш баланс: {balance:.2f} USDT"
        game_outcome = "❌ Проигрыш"

    # Логируем результат игры в канал
    channel_id = -1002311474812
    log_message = (f"🎰 Игра завершена!\n"
                   f"👤 Игрок: @{username}\n"
                   f"🎮 Игра: {game_choice.replace('_game', '').title()}\n"
                   f"💰 Ставка: {current_bet:.2f} USDT\n"
                   f"🎲 Выпало: {result}\n"
                   f"🏆 Итог: {game_outcome}")

    await bot.send_message(channel_id, log_message)

    # Показываем результат и возвращаем клавиатуру с играми
    await callback.answer(result_message, show_alert=True)
    updated_user_data = cursor.execute("SELECT balance, current_bet FROM user WHERE telegram_id = ?",
                                       (telegram_id,)).fetchone()
    updated_balance, updated_bet = updated_user_data
    await callback.message.answer("Вы вернулись в меню!", reply_markup=get_game_keyboard(updated_bet))


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

    if callback.data == 'increase_bet':
        if current_bet >= 30:
            await callback.answer("Ставка уже максимальная!", show_alert=False)
            return
        current_bet = min(current_bet * 2, 30)

    elif callback.data == 'decrease_bet':
        if current_bet <= 0.1:
            await callback.answer("Ставка уже минимальная!", show_alert=False)
            return
        current_bet = max(current_bet / 2, 0.1)

    cursor.execute("UPDATE user SET current_bet = ? WHERE telegram_id = ?", (current_bet, telegram_id))
    conn.commit()

    kb = get_game_keyboard(current_bet)

    new_message = f"Выберите игру или измените ставку:\nТекущая ставка: {current_bet:.1f} USDT"

    if callback.message.text != new_message:
        await callback.message.edit_text(new_message, reply_markup=kb)

    await callback.answer()


@router.callback_query(lambda c: c.data == 'enter_bet')
async def enter_bet(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    sent_message = await callback.message.edit_text("Введите сумму ставки (от 0.1 до 30 USDT):")
    await state.update_data(bot_message_id=sent_message.message_id)

    await state.set_state(BetState.waiting_for_bet)


@router.message(BetState.waiting_for_bet)
async def process_bet_input(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    bet_amount = message.text.replace(',', '.')

    try:
        bet_amount = float(bet_amount)
    except ValueError:
        await message.answer("Ошибка! Введите число от 0.1 до 30 USDT.")
        return

    if bet_amount < 0.1 or bet_amount > 30:
        await message.answer("Ошибка! Введите сумму от 0.1 до 30 USDT.")
        return

    cursor.execute("UPDATE user SET current_bet = ? WHERE telegram_id = ?", (bet_amount, telegram_id))
    conn.commit()

    await message.delete()

    state_data = await state.get_data()
    bot_message_id = state_data.get("bot_message_id")
    if bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, bot_message_id)
        except:
            pass

    kb = get_game_keyboard(bet_amount)
    sent_message = await message.answer(f"Ставка установлена: {bet_amount:.1f} USDT", reply_markup=kb)

    await state.clear()


@router.callback_query(lambda c: c.data == 'reset_bet')
async def reset_bet(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    default_bet = 1.0

    cursor.execute("UPDATE user SET current_bet = ? WHERE telegram_id = ?", (default_bet, telegram_id))
    conn.commit()

    kb = get_game_keyboard(default_bet)
    await callback.message.edit_text(f"Ставка сброшена: {default_bet:.1f} USDT", reply_markup=kb)
    await callback.answer()


def get_game_keyboard(current_bet):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='🎲 Кости', callback_data='bones_game'))
    kb.row(InlineKeyboardButton(text='🏀 Баскетбол', callback_data='basketball_game'))
    kb.row(InlineKeyboardButton(text='🎳 Боулинг', callback_data='bowling_game'))
    kb.row(InlineKeyboardButton(text='🎯 Дартс', callback_data='darts_game'))
    kb.row(InlineKeyboardButton(text='⚽ Футбол', callback_data='football_game'))
    kb.row(InlineKeyboardButton(text='⬆️', callback_data='increase_bet'))
    kb.add(
        InlineKeyboardButton(text=f'{current_bet:.1f} USDT', callback_data='enter_bet'),
        InlineKeyboardButton(text='⬇️', callback_data='decrease_bet'),
    )
    kb.row(InlineKeyboardButton(text='🔄 Сбросить ставку', callback_data='reset_bet'))
    kb.row(InlineKeyboardButton(text='🔙 Назад', callback_data='home'))
    return kb.as_markup()
