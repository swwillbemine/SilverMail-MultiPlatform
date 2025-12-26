import os
import json
import random
import string
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Import fungsi baru dari database
from database import get_emails_for_user, get_user_stats, register_user, init_db

# --- SETUP AWAL ---
# Pastikan DB terinit dengan tabel baru
init_db()

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# Config Loader (Sama seperti sebelumnya)
def load_json_file(filename, default_value):
    try:
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return default_value

ALLOWED_DOMAINS = load_json_file('domains.json', ["localhost"])
NAME_LIST = load_json_file('names.json', ["user"])
ADMIN_CONFIG = load_json_file('config.json', {
    "admin_username": "admin",
    "admin_password": "password",
    "secret_key": "fallback_secret_key" # Default jika config hilang
})

app.secret_key = ADMIN_CONFIG.get("secret_key")

ADMIN_USERNAME = ADMIN_CONFIG.get("admin_username")
ADMIN_PASSWORD = ADMIN_CONFIG.get("admin_password")


# Helper Log Reader
def get_system_logs(lines=100):
    log_path = os.path.join(base_dir, 'system.log')
    if not os.path.exists(log_path):
        return ["Log file not found."]
    
    try:
        # Membaca N baris terakhir (sederhana)
        with open(log_path, 'r') as f:
            all_lines = f.readlines()
            return all_lines[-lines:][::-1] # Ambil terakhir & balik urutan (terbaru diatas)
    except Exception as e:
        return [f"Error reading logs: {str(e)}"]

# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    current_email = session.get('email')
    return render_template('index.html', domains=ALLOWED_DOMAINS, email=current_email)

@app.route('/generate', methods=['POST'])
def generate_email():
    data = request.json
    username = data.get('username', '').strip()
    domain = data.get('domain')

    if domain not in ALLOWED_DOMAINS:
        return jsonify({"error": "Invalid domain"}), 400

    if not username:
        if NAME_LIST:
            base_name = random.choice(NAME_LIST)
            suffix = str(random.randint(10, 999))
            username = f"{base_name}{suffix}"
        else:
            username = ''.join(random.choices(string.ascii_lowercase, k=8))
    
    full_email = f"{username}@{domain}".lower()
    session['email'] = full_email
    
    # [BARU] Catat User ke Database
    user_ip = request.remote_addr
    register_user(full_email, user_ip)
    
    display_name = username.capitalize()
    if 'suffix' in locals():
        display_name = username.replace(suffix, '').capitalize()

    return jsonify({"email": full_email, "fullName": display_name})

@app.route('/emails', methods=['GET'])
def get_emails():
    current_email = session.get('email')
    if not current_email: return jsonify([])
    return jsonify(get_emails_for_user(current_email.lower()))

# --- ADMIN ROUTES ---
@app.route('/temp/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == ADMIN_USERNAME and pwd == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/temp')
@login_required
def admin_dashboard():
    # Ambil Statistik User
    user_stats = get_user_stats()
    
    # Ambil Logs
    system_logs = get_system_logs()
    
    return render_template('admin.html', stats=user_stats, logs=system_logs)

@app.route('/temp/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/api/admin/data')
@login_required
def api_admin_data():
    """API untuk Auto-Refresh Dashboard"""
    # 1. Ambil Stats User
    stats = get_user_stats()
    
    # 2. Ambil Logs
    logs = get_system_logs(lines=100)
    
    return jsonify({
        "stats": stats,
        "logs": logs
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)