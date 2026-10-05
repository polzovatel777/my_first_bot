import sqlite3

DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT
        )
    """)
    # Таблица заявок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            phone TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int, username: str, first_name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username or "", first_name or "")
    )
    conn.commit()
    conn.close()

def get_all_users():
    """Возвращает список кортежей [(user_id,), ...] всех пользователей из базы данных."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM users")
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(f"Ошибка чтения пользователей из БД: {e}")
        return []
    finally:
        conn.close()

def add_request(user_id: int, name: str, phone: str, comment: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Исправлено: добавлены все 4 знака вопроса (?, ?, ?, ?)
    cursor.execute(
        "INSERT INTO requests (user_id, name, phone, comment) VALUES (?, ?, ?, ?)",
        (user_id, name, phone, comment)
    )
    conn.commit()
    conn.close()

def get_all_requests(limit: int = 10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, phone, comment, created_at FROM requests ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows