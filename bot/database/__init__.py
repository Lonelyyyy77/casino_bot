import sqlite3

DB_NAME = 'main12.db'

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()


def initialize_database():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            telegram_id INTEGER NOT NULL         
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_ip TEXT NOT NULL,
            username TEXT NOT NULL,
            telegram_id INTEGER NOT NULL,
            language_layout TEXT NOT NULL,
            device TEXT NOT NULL,
            balance INTEGER DEFAULT 0,
            has_agreed_rules INTEGER DEFAULT 0,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reward_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount INTEGER NOT NULL,  
            remaining_uses INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reward_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reward_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(reward_id, user_id)
        )
    ''')

    conn.commit()
    conn.close()


