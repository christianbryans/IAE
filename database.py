import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

def get_db_connection():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists('data.db'):
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
        
        # Create bookings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                passenger_name TEXT NOT NULL,
                departure_airport TEXT NOT NULL,
                destination_airport TEXT NOT NULL,
                travel_date DATE NOT NULL,
                seat_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create seat_selections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seat_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                passenger_name TEXT NOT NULL,
                seat_number TEXT NOT NULL,
                selected_on DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings (id)
            )
        ''')
        
        # Create payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                method TEXT NOT NULL,
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
                passenger_name TEXT NOT NULL,
                departure_airport TEXT NOT NULL,
                destination_airport TEXT NOT NULL,
                reason TEXT NOT NULL,
                cancelled_on DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings (id)
            )
        ''')
        
        # Create refunds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                passenger_name TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                refund_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    else:
        # Database exists, check for schema updates
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get list of existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        # Add new columns to existing tables if they don't exist
        if 'users' in existing_tables:
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN phone TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        if 'bookings' in existing_tables:
            try:
                cursor.execute('ALTER TABLE bookings ADD COLUMN passenger_name TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE bookings ADD COLUMN seat_number TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        if 'seat_selections' in existing_tables:
            try:
                cursor.execute('ALTER TABLE seat_selections ADD COLUMN passenger_name TEXT')
            except sqlite3.OperationalError:
                pass  # Column already exists
        
        if 'payments' in existing_tables:
            try:
                cursor.execute('ALTER TABLE payments ADD COLUMN amount INTEGER')
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute('ALTER TABLE payments ADD COLUMN payment_date DATE')
            except sqlite3.OperationalError:
                pass  # Column already exists
        
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