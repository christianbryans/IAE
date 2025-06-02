import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

def get_db_connection():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # If database exists, remove it to recreate with new schema
    if os.path.exists("data.db"):
        os.remove("data.db")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create bookings table with user_id
    cursor.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        departure_airport TEXT NOT NULL,
        destination_airport TEXT NOT NULL,
        booking_date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Create reschedule history table
    cursor.execute('''CREATE TABLE IF NOT EXISTS reschedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        old_date TEXT NOT NULL,
        new_date TEXT NOT NULL,
        reschedule_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
    )''')
    
    conn.commit()
    conn.close()

def create_user(username, password, full_name, email, phone=None, address=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, password, full_name, email, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, generate_password_hash(password), full_name, email, phone, address))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_password(user, password):
    if user is None:
        return False
    return check_password_hash(user['password'], password)