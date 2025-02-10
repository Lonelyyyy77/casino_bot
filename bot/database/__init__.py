import sqlite3

DB_NAME = 'bot1.db'

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
            telegram_id INTEGER NOT NULL UNIQUE,
            language_layout TEXT NOT NULL,
            device TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            has_agreed_rules INTEGER DEFAULT 0,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referrer_id INTEGER,
            referral_earnings REAL DEFAULT 0.0,
            referral_percent REAL DEFAULT 10.0,
            total_bets REAL DEFAULT 0.0,
            current_bet REAL DEFAULT 0.5,
            is_frizzed_checkout INTEGER DEFAULT 0,
            has_completed_captcha INTEGER DEFAULT 0
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL, 
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            percentage INTEGER DEFAULT 10.0
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS captcha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            expected_answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT,
            user_id INTEGER,
            jpc_amount REAL,
            status TEXT
        )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section TEXT UNIQUE NOT NULL,
                image_url TEXT NOT NULL
            )
        """)

    conn.commit()
    conn.close()


