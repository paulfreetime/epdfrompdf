import sqlite3

def init_db(db_path="gwp_data.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS gwp_totals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            page INTEGER,
            header TEXT,
            line TEXT
        )
    """)
    conn.commit()
    return conn
