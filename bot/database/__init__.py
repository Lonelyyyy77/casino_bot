import sqlite3

DB_NAME = 'main2.db'


def initialize_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

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
            has_agreed_rules INTEGER DEFAULT 0                  
        );
    ''')

    conn.commit()
    conn.close()


