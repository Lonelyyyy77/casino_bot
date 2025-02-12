import math
import sqlite3

from aiogram import Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database import DB_NAME
from bot.database.admin.admin import get_mailings_page

router = Router()
PAGE_SIZE = 3


def get_mailings_page(page: int):
    """
    Возвращает кортеж:
      (список рассылок для указанной страницы, общее число страниц, общее число рассылок)
    При этом для рассылок с вознаграждением берётся актуальное значение оставшихся активаций
    из таблицы reward_buttons (столбец remaining_uses).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM mailings")
    total_count = cursor.fetchone()[0]
    total_pages = math.ceil(total_count / PAGE_SIZE) if total_count > 0 else 1

    offset = page * PAGE_SIZE

    cursor.execute("""
        SELECT 
            m.id, 
            m.text, 
            m.media_type, 
            m.reward_amount, 
            COALESCE(rb.remaining_uses, m.reward_uses) AS remaining_uses,
            m.timestamp 
        FROM mailings m
        LEFT JOIN reward_buttons rb ON m.reward_button_id = rb.id
        ORDER BY m.timestamp DESC 
        LIMIT ? OFFSET ?
    """, (PAGE_SIZE, offset))
    mailings = cursor.fetchall()
    conn.close()
    return mailings, total_pages, total_count


def build_mailings_text(mailings, current_page: int, total_pages: int, total_count: int) -> str:
    """
    Формирует красиво оформленный HTML‑текст статистики рассылок.
    В шапке выводится номер страницы, общее количество страниц и общее число рассылок.
    Для каждой рассылки выводится:
      • ID,
      • дата,
      • тип медиа,
      • краткий текст (первые 50 символов),
      • информация о вознаграждении (если задано), где показывается сумма вознаграждения и оставшиеся активации.
    """
    if not mailings:
        return "Нет рассылок для отображения."

    text = "📊 <b>Статистика рассылок</b>\n"
    text += f"Страница: {current_page + 1} из {total_pages}\n"
    text += f"Всего рассылок: {total_count}\n\n"

    for mailing in mailings:
        mailing_id, mailing_text, media_type, reward_amount, remaining_uses, timestamp = mailing
        text_preview = mailing_text if len(mailing_text) < 50 else mailing_text[:50] + "..."
        text += f"🆔 <b>ID:</b> {mailing_id}\n"
        text += f"🕒 <b>Дата:</b> {timestamp}\n"
        text += f"📷 <b>Тип медиа:</b> {media_type or 'Нет'}\n"
        text += f"✉️ <b>Текст:</b> {text_preview}\n"
        if reward_amount and remaining_uses is not None:
            text += f"💰 <b>Вознаграждение:</b> {reward_amount} JPC, <b>Осталось активаций:</b> {remaining_uses}\n"
        text += "\n"
    return text


def build_pagination_kb(current_page: int, total_pages: int) -> InlineKeyboardBuilder:
    """
    Формирует inline-клавиатуру для перелистывания страниц статистики рассылок.
    Если доступны и предыдущая, и следующая страницы, выводятся две кнопки в одной строке.
    """
    kb = InlineKeyboardBuilder()
    if current_page > 0 and current_page < total_pages - 1:
        kb.row(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"mailing_settings:{current_page - 1}"
            ),
            types.InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"mailing_settings:{current_page + 1}"
            )
        )
    elif current_page > 0:
        kb.add(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"mailing_settings:{current_page - 1}"
            )
        )
    elif current_page < total_pages - 1:
        kb.add(
            types.InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"mailing_settings:{current_page + 1}"
            )
        )
    return kb


@router.callback_query(lambda c: c.data.startswith("mailing_settings"))
async def mailing_settings_handler(callback: types.CallbackQuery):
    """
    Обработчик для просмотра статистики рассылок.
    При нажатии на кнопку «⚙️ Настройки рассылки» или кнопки навигации,
    сообщение редактируется с информацией о соответствующей странице рассылок.
    """
    data = callback.data
    try:
        if data == "mailing_settings":
            current_page = 0
        else:
            current_page = int(data.split(":")[1])
    except Exception:
        current_page = 0

    mailings, total_pages, total_count = get_mailings_page(current_page)
    text = build_mailings_text(mailings, current_page, total_pages, total_count)
    kb = build_pagination_kb(current_page, total_pages)

    await callback.message.edit_text(
        text=text, reply_markup=kb.as_markup(), parse_mode="HTML"
    )
    await callback.answer()
