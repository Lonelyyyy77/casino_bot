from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.admin.admin import set_menu_image
from bot.states.admin.states import UploadImageState

router = Router()


@router.callback_query(lambda c: c.data == "admin_set_image")
async def upload_image_start(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🏠 Главная страница", callback_data="set_image_home"),
        InlineKeyboardButton(text="🎮 Игры", callback_data="set_image_games")
    )
    kb.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="set_image_profile")
    )

    await callback.message.edit_text("Выберите раздел для загрузки изображения:", reply_markup=kb.as_markup())
    await state.set_state(UploadImageState.waiting_for_section)


@router.callback_query(lambda c: c.data.startswith("set_image_"))
async def upload_image_section(callback: types.CallbackQuery, state: FSMContext):
    section = callback.data.split("_")[-1]

    await state.update_data(section=section)
    await callback.message.edit_text("Теперь отправьте изображение для этого раздела.")
    await state.set_state(UploadImageState.waiting_for_image)


@router.message(UploadImageState.waiting_for_image, F.photo)
async def upload_image_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    section = data["section"]

    image_file_id = message.photo[-1].file_id

    set_menu_image(section, image_file_id)

    await message.answer(f"✅ Изображение для раздела '{section}' успешно обновлено!")
    await state.clear()
