import os
import json
import random
import string
import time
import psutil
import platform
import socket
import subprocess
import urllib.request
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

# --- CONFIG & DATA HELPER ---
def load_json_file(filename, default_value):
    try:
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return default_value

def save_json_file(filename, data):
    try:
        file_path = os.path.join(base_dir, filename)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except:
        return False

# Load Initial Configs
ALLOWED_DOMAINS = load_json_file('domains.json', ["localhost"])
NAME_LIST = load_json_file('names.json', ["user"])
ADMIN_CONFIG = load_json_file('config.json', {
    "admin_username": "admin", 
    "admin_password": "password",
    "secret_key": "secret",
    "app_name": "SilverMail"
})

app.secret_key = ADMIN_CONFIG.get("secret_key")
ADMIN_USERNAME = ADMIN_CONFIG.get("admin_username")
ADMIN_PASSWORD = ADMIN_CONFIG.get("admin_password")
APP_NAME = ADMIN_CONFIG.get("app_name", "SilverMail")

# --- SYSTEM METRICS HELPER ---
def get_public_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode('utf8')
    except:
        return "Unknown (Timeout)"

def get_detailed_metrics():
    """Mengambil data real-time VPS Lengkap"""
    # CPU
    cpu_usage = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq()
    cpu_freq_current = f"{round(cpu_freq.current, 0)} Mhz" if cpu_freq else "N/A"
    
    # RAM
    ram = psutil.virtual_memory()
    
    # DISK
    disk = psutil.disk_usage('/')
    
    # UPTIME
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_hours = round(uptime_seconds / 3600, 1)

    # NETWORK
    net = psutil.net_io_counters()
    net_sent = round(net.bytes_sent / (1024**2), 1)
    net_recv = round(net.bytes_recv / (1024**2), 1)

    # OS INFO
    os_info = f"{platform.system()} {platform.release()}"
    
    return {
        "cpu_usage": cpu_usage,
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_freq": cpu_freq_current,
        "ram_percent": ram.percent,
        "ram_used": round(ram.used / (1024**3), 2),
        "ram_total": round(ram.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_free": round(disk.free / (1024**3), 1),
        "uptime": f"{uptime_hours} Hours",
        "net_sent": f"{net_sent} MB",
        "net_recv": f"{net_recv} MB",
        "os_info": os_info,
        "hostname": socket.gethostname(),
        "public_ip": get_public_ip() # Note: Ini sedikit memperlambat request, idealnya dicache
    }

# --- AUTH ---
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
    # Reload config untuk memastikan nama aplikasi terupdate
    cfg = load_json_file('config.json', {})
    current_app_name = cfg.get('app_name', 'SilverMail')
    
    # Reload domains
    domains = load_json_file('domains.json', ["localhost"])
    
    current_email = session.get('email')
    return render_template('index.html', domains=domains, email=current_email, app_name=current_app_name)

@app.route('/generate', methods=['POST'])
def generate_email():
    domains = load_json_file('domains.json', []) # Always load fresh domains
    data = request.json
    username = data.get('username', '').strip()
    domain = data.get('domain')

    if domain not in domains:
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
        
        # Load credentials fresh from file (in case changed manually)
        cfg = load_json_file('config.json', {})
        real_user = cfg.get('admin_username', ADMIN_USERNAME)
        real_pass = cfg.get('admin_password', ADMIN_PASSWORD)

        if user == real_user and pwd == real_pass:
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

# --- ADMIN API ---

@app.route('/api/admin/data')
@login_required
def api_admin_data():
    stats = get_user_stats()
    logs = get_system_logs(lines=100)
    metrics = get_detailed_metrics() # Includes Public IP
    db_size = get_db_size()
    
    # Load settings
    cfg = load_json_file('config.json', {})
    domains = load_json_file('domains.json', [])

    return jsonify({
        "stats": stats,
        "logs": logs,
        "metrics": metrics,
        "db_size": f"{db_size} MB",
        "settings": {
            "app_name": cfg.get("app_name", "SilverMail"),
            "domains": domains
        }
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
    delete_user_data(data.get('email'))
    return jsonify({"status": "success"})

@app.route('/api/admin/clear_logs', methods=['POST'])
@login_required
def api_clear_logs():
    clear_system_logs()
    return jsonify({"status": "success"})

# --- SETTINGS API ---

@app.route('/api/admin/update_settings', methods=['POST'])
@login_required
def api_update_settings():
    data = request.json
    new_name = data.get('app_name')
    
    if new_name:
        cfg = load_json_file('config.json', {})
        cfg['app_name'] = new_name
        save_json_file('config.json', cfg)
        return jsonify({"status": "success", "message": "App name updated"})
    return jsonify({"error": "Invalid data"}), 400

@app.route('/api/admin/add_domain', methods=['POST'])
@login_required
def api_add_domain():
    data = request.json
    new_domain = data.get('domain', '').strip().lower()
    
    if new_domain:
        domains = load_json_file('domains.json', [])
        if new_domain not in domains:
            domains.append(new_domain)
            save_json_file('domains.json', domains)
            return jsonify({"status": "success"})
        return jsonify({"error": "Domain already exists"}), 400
    return jsonify({"error": "Invalid domain"}), 400

@app.route('/api/admin/remove_domain', methods=['POST'])
@login_required
def api_remove_domain():
    data = request.json
    domain_to_remove = data.get('domain')
    
    domains = load_json_file('domains.json', [])
    if domain_to_remove in domains:
        domains.remove(domain_to_remove)
        save_json_file('domains.json', domains)
        return jsonify({"status": "success"})
    return jsonify({"error": "Domain not found"}), 400

@app.route('/api/admin/restart_system', methods=['POST'])
@login_required
def api_restart_system():
    # Restart service via systemctl (requires root)
    try:
        subprocess.Popen(['systemctl', 'restart', 'silvermail'])
        return jsonify({"status": "success", "message": "Server restarting..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)