import os
import json
import random
import string
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Import fungsi database
from database import get_emails_for_user, get_user_stats, register_user, init_db, get_system_logs

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
    "secret_key": "default_secret_key"
})

app.secret_key = ADMIN_CONFIG.get("secret_key")
ADMIN_USERNAME = ADMIN_CONFIG.get("admin_username")
ADMIN_PASSWORD = ADMIN_CONFIG.get("admin_password")


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
    
    # Catat User
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

# --- ADMIN ROUTES (UPDATED: /temp -> /admin) ---

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
    # Render halaman awal saja, data diambil via API
    return render_template('admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# --- ADMIN API (DATA) ---

@app.route('/api/admin/data')
@login_required
def api_admin_data():
    """API untuk Auto-Refresh Dashboard Utama"""
    stats = get_user_stats()
    logs = get_system_logs(lines=100)
    return jsonify({
        "stats": stats,
        "logs": logs
    })

@app.route('/api/admin/inbox/<path:email>')
@login_required
def api_admin_user_inbox(email):
    """API BARU: Mengambil isi email user tertentu untuk Admin"""
    emails = get_emails_for_user(email)
    return jsonify(emails)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)