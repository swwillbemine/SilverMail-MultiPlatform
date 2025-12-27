import os
import json
import random
import string
import time
import psutil # Library untuk cek CPU/RAM Real
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Import fungsi database
from database import (get_emails_for_user, get_user_stats, register_user, 
                      init_db, get_system_logs, get_db_size, delete_user_data, clear_system_logs)

# --- SETUP AWAL ---
init_db()

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

# Load Config
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
    "secret_key": "secret"
})

app.secret_key = ADMIN_CONFIG.get("secret_key")
ADMIN_USERNAME = ADMIN_CONFIG.get("admin_username")
ADMIN_PASSWORD = ADMIN_CONFIG.get("admin_password")

# --- HELPER SYSTEM MONITOR ---
def get_server_metrics():
    """Mengambil data real-time VPS"""
    # CPU
    cpu_usage = psutil.cpu_percent(interval=None)
    
    # RAM
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    ram_total = round(ram.total / (1024**3), 2) # GB
    ram_used = round(ram.used / (1024**3), 2)   # GB
    
    # DISK
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent
    
    # UPTIME
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_hours = round(uptime_seconds / 3600, 1)

    # NETWORK (Bytes Sent/Recv since boot)
    net = psutil.net_io_counters()
    net_sent = round(net.bytes_sent / (1024**2), 1) # MB
    net_recv = round(net.bytes_recv / (1024**2), 1) # MB

    return {
        "cpu": cpu_usage,
        "ram_percent": ram_usage,
        "ram_detail": f"{ram_used}/{ram_total} GB",
        "disk": disk_usage,
        "uptime": f"{uptime_hours} Hours",
        "net_sent": f"{net_sent} MB",
        "net_recv": f"{net_recv} MB"
    }

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
    
    register_user(full_email, request.remote_addr)
    
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
@app.route('/admin/login', methods=['GET', 'POST'])
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

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# --- ADMIN API (DATA REAL-TIME) ---

@app.route('/api/admin/data')
@login_required
def api_admin_data():
    # 1. User Stats
    stats = get_user_stats()
    
    # 2. System Logs
    logs = get_system_logs(lines=100)
    
    # 3. Real Server Metrics (CPU, RAM, etc)
    server_metrics = get_server_metrics()
    
    # 4. DB Size
    db_size = get_db_size()

    return jsonify({
        "stats": stats,
        "logs": logs,
        "metrics": server_metrics,
        "db_size": f"{db_size} MB"
    })

@app.route('/api/admin/inbox/<path:email>')
@login_required
def api_admin_user_inbox(email):
    emails = get_emails_for_user(email)
    return jsonify(emails)

@app.route('/api/admin/delete_user', methods=['POST'])
@login_required
def api_delete_user():
    data = request.json
    email = data.get('email')
    if email:
        delete_user_data(email)
        return jsonify({"status": "success"})
    return jsonify({"error": "No email provided"}), 400

@app.route('/api/admin/clear_logs', methods=['POST'])
@login_required
def api_clear_logs():
    clear_system_logs()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)