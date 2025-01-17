import sqlite3

from database import DB_NAME


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