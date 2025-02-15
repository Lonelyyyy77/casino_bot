import sqlite3

from database import DB_NAME


def add_user_to_db(db_name, telegram_id, local_ip, username, language_layout, device, referrer_id):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM user WHERE telegram_id = ?", (telegram_id,))
    user_exists = cursor.fetchone()

    if user_exists:
        conn.close()
        return False

    cursor.execute('''
        INSERT INTO user (telegram_id, local_ip, username, language_layout, device, referrer_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, local_ip, username, language_layout, device, referrer_id))
    conn.commit()
    conn.close()
    return True



def update_user_balance(telegram_id: int, jpc_amount: int, db_name: str = DB_NAME):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE user
        SET balance = balance + ?
        WHERE telegram_id = ?
    """, (jpc_amount, telegram_id))

    conn.commit()
    conn.close()


def get_user_balance(telegram_id: int, db_name: str = DB_NAME):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT balance FROM user
        WHERE telegram_id = ?
    """, (telegram_id,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else 0
