import sqlite3

from bot.database import DB_NAME


def add_admin(db_name, telegram_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM admin WHERE telegram_id = ?", (telegram_id,))
    admin_exists = cursor.fetchone()

    if not admin_exists:
        cursor.execute("INSERT INTO admin (telegram_id) VALUES (?);", (telegram_id,))
        conn.commit()
        print(f"Администратор с ID {telegram_id} добавлен.")
    else:
        print(f"Администратор с ID {telegram_id} уже существует.")

    conn.close()


def is_admin(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM admin WHERE telegram_id = ?", (telegram_id,))
    admin_exists = cursor.fetchone()

    conn.close()
    return bool(admin_exists)


def get_user_statistics():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM user WHERE registration_date >= datetime('now', '-1 day')")
    users_last_day = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user WHERE registration_date >= datetime('now', '-7 days')")
    users_last_week = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user WHERE registration_date >= datetime('now', '-1 month')")
    users_last_month = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user")
    total_users = cursor.fetchone()[0]

    conn.close()

    return {
        "last_day": users_last_day,
        "last_week": users_last_week,
        "last_month": users_last_month,
        "total": total_users
    }


def set_menu_image(section: str, image_url: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO menu_images (section, image_url) 
        VALUES (?, ?) 
        ON CONFLICT(section) DO UPDATE SET image_url = excluded.image_url
    """, (section, image_url))

    conn.commit()
    conn.close()