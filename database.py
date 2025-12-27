import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "emails.db")
LOG_FILE = os.path.join(BASE_DIR, "system.log")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            sender TEXT,
            subject TEXT,
            body TEXT,
            received_at TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            created_at TIMESTAMP,
            ip_address TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- FUNGSI EMAIL ---
def save_email(recipient, sender, subject, body):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO emails (recipient, sender, subject, body, received_at) VALUES (?, ?, ?, ?, ?)',
              (recipient, sender, subject, body, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_emails_for_user(email_address):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM emails WHERE recipient = ? ORDER BY id DESC', (email_address,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- FUNGSI USER & STATS ---
def register_user(email_address, ip_address):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (email, created_at, ip_address) VALUES (?, ?, ?)',
              (email_address, datetime.now().isoformat(), ip_address))
    conn.commit()
    conn.close()

def get_user_stats():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    query = '''
        SELECT u.email, u.created_at, u.ip_address, COUNT(e.id) as inbox_count 
        FROM users u 
        LEFT JOIN emails e ON u.email = e.recipient 
        GROUP BY u.email 
        ORDER BY u.created_at DESC
    '''
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_user_data(email):
    """Menghapus user dan semua emailnya"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM emails WHERE recipient = ?', (email,))
    c.execute('DELETE FROM users WHERE email = ?', (email,))
    conn.commit()
    conn.close()

def get_db_size():
    """Mengambil ukuran file database dalam MB"""
    if os.path.exists(DB_NAME):
        size_bytes = os.path.getsize(DB_NAME)
        return round(size_bytes / (1024 * 1024), 2) # Convert to MB
    return 0

# --- FUNGSI LOGS ---
def get_system_logs(lines=200):
    if not os.path.exists(LOG_FILE):
        return ["Log file not found at: " + LOG_FILE]
    try:
        with open(LOG_FILE, 'r') as f:
            all_lines = f.readlines()
            return all_lines[-lines:][::-1]
    except Exception as e:
        return [f"Error reading logs: {str(e)}"]

def clear_system_logs():
    """Menghapus isi log"""
    open(LOG_FILE, 'w').close()