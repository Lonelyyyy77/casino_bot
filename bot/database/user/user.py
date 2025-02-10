import sqlite3

from bot.database import DB_NAME


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


def get_user_by_telegram_id(telegram_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if row is None:
        return None

    return {
        'id': row[0],
        'local_ip': row[1],
        'username': row[2],
        'telegram_id': row[3],
        'language_layout': row[4],
        'device': row[5],
        'balance': row[6],
        'has_agreed_rules': row[7],
        'registration_date': row[8],
        'referrer_id': row[9],
        'referral_earnings': row[10],
        'referral_percent': row[11],
        'total_bets': row[12],
        'current_bet': row[13],
        'is_frizzed_checkout': row[14],
        'has_completed_captcha': row[15]
    }


def get_user_by_username(username: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        'id': row[0],
        'local_ip': row[1],
        'username': row[2],
        'telegram_id': row[3],
        'language_layout': row[4],
        'device': row[5],
        'balance': row[6],
        'has_agreed_rules': row[7],
        'registration_date': row[8],
        'referrer_id': row[9],
        'referral_earnings': row[10],
        'referral_percent': row[11],
        'total_bets': row[12],
        'current_bet': row[13],
        'is_frizzed_checkout': row[14],
        'has_completed_captcha': row[15]
    }


def get_menu_image(section: str):
    """Получает URL изображения для указанного раздела."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT image_url FROM menu_images WHERE section = ?", (section,))
    result = cursor.fetchone()

    conn.close()
    return result[0] if result else None