import sqlite3

def get_db_connection():
    conn = sqlite3.connect("data.db")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        destination TEXT NOT NULL,
        date TEXT NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS reschedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        new_date TEXT NOT NULL,
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
    )''')
    conn.commit()
    conn.close()