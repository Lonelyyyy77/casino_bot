from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.admin.admin import is_admin
from bot.database.user.user import add_user_to_db, get_user_balance

router = Router()


@router.message(CommandStart())
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    username = message.from_user.username or "Не указано"

    web_app_url = f"https://8fa6-88-154-11-236.ngrok-free.app?telegram_id={telegram_id}"

    local_ip = "Неизвестно"
    device = "Неизвестно"

    language_layout = message.from_user.language_code

    is_new_user = add_user_to_db(
        db_name=DB_NAME,
        telegram_id=telegram_id,
        local_ip=local_ip,
        username=username,
        language_layout=language_layout,
        device=device
    )

    kbds = InlineKeyboardBuilder()
    kbds.row(InlineKeyboardButton(text='Игры', callback_data='games'))
    kbds.row(InlineKeyboardButton(text='Пополнить баланс', callback_data='replenish'))
    kbds.row(InlineKeyboardButton(text='Открыть веб приложение', web_app=WebAppInfo(url=web_app_url)))

    if is_admin(message.from_user.id):
        kbds.row(InlineKeyboardButton(text="Админ-панель", callback_data="admin_panel"))

    if is_new_user:
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text='ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ', url='https://telegra.ph/LICENZIONNOE-SOGLASHENIE-WIN-SHARK-01-09'))
        kb.row(InlineKeyboardButton(text='✅Соглашаюсь✅', callback_data='accept'))

        await message.answer(
            "**Нажимая кнопку ниже, вы соглашаетесь с правилами:**\n\n"
            "1) **Запрещены мульти-аккаунты!**\n"
            "2) **Запрещены махинации, багаюз!**\n"
            "3) **Запрещён обман администрации!**",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

    else:
        balance_jpc = get_user_balance(telegram_id)
        balance_usd = balance_jpc

        await message.answer(
            f"Привет! Ваш текущий баланс: {balance_jpc} JPC (${balance_usd}).\nВыберите, что хотите сделать:",
            reply_markup=kbds.as_markup()
        )


@router.callback_query(lambda c: c.data == 'accept')
async def accept_handler(callback: types.CallbackQuery):
    await callback.message.answer("Нажми на команду:\n\n/start\n/start\n/start")
