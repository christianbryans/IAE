import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

def get_db_connection():
    db_path = os.path.join('data', 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create airlines table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS airlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            logo_url TEXT,
            base_price INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            airline_id INTEGER NOT NULL,
            passenger_name TEXT NOT NULL,
            departure_airport TEXT NOT NULL,
            destination_airport TEXT NOT NULL,
            booking_date DATE NOT NULL,
            seat_number TEXT,
            total_price INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (airline_id) REFERENCES airlines (id)
        )
    ''')
    
    # Create payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            method TEXT NOT NULL,
            status TEXT NOT NULL,
            payment_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
    ''')
    
    # Create cancellations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cancellations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            refund_amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def register_user(username, password, full_name, email, phone=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        hashed_password = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, password, full_name, email, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hashed_password, full_name, email, phone))
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

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_profile(user_id, full_name, email, phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users 
            SET full_name = ?, email = ?, phone = ?
            WHERE id = ?
        ''', (full_name, email, phone, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_bookings(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, u.email, u.phone
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    ''', (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    return bookings

def get_booking_by_id(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,))
    booking = cursor.fetchone()
    conn.close()
    return booking

def get_seat_selection_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ss.*, b.passenger_name 
        FROM seat_selections ss
        JOIN bookings b ON ss.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY ss.selected_on DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

def get_payment_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, b.passenger_name 
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY p.payment_date DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

def get_cancellation_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, b.passenger_name 
        FROM cancellations c
        JOIN bookings b ON c.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY c.cancelled_on DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

def get_refund_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, b.passenger_name 
        FROM refunds r
        JOIN bookings b ON r.booking_id = b.id
        WHERE b.user_id = ?
        ORDER BY r.refund_date DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

if __name__ == '__main__':
    init_db()