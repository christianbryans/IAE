import os
import sqlite3

# Get the absolute path to the data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
db_path = os.path.join(data_dir, 'database.db')

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Add new columns to booking table if they don't exist
try:
    cursor.execute('ALTER TABLE booking ADD COLUMN base_price FLOAT NOT NULL DEFAULT 0.0')
    cursor.execute('ALTER TABLE booking ADD COLUMN total_price FLOAT NOT NULL DEFAULT 0.0')
    print("Added new price columns to booking table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Price columns already exist")
    else:
        raise e

# Commit changes and close connection
conn.commit()
conn.close()

print("Database migration completed successfully!") 