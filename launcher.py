import multiprocessing
import subprocess
import time
import os
import signal
import sys
from smtp_runner import run_smtp_server

# File Log
LOG_FILE = "system.log"

processes = []

def log_writer(message):
    """Menulis log ke file dan console"""
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    full_msg = f"{timestamp} {message}"
    print(full_msg) # Ke Console/Systemd
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n") # Ke File

def start_smtp():
    # Redirect stdout/stderr SMTP ke file log (Manual handling di script SMTP lebih baik, tapi ini wrapper sederhana)
    sys.stdout = open(LOG_FILE, 'a')
    sys.stderr = open(LOG_FILE, 'a')
    run_smtp_server()

def start_gunicorn():
    log_writer("[Launcher] Starting Gunicorn on Port 80...")
    # Kita pipe output Gunicorn ke file log
    with open(LOG_FILE, "a") as f:
        subprocess.run(
            ["/usr/local/bin/gunicorn", "--workers", "3", "--bind", "0.0.0.0:80", "--access-logfile", LOG_FILE, "--error-logfile", LOG_FILE, "app:app"]
        )

def signal_handler(sig, frame):
    log_writer("[Launcher] Stopping Services...")
    for p in processes:
        if isinstance(p, multiprocessing.Process):
            p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    # Pastikan file log ada
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log_writer("[Launcher] Starting Services...")

    p_smtp = multiprocessing.Process(target=start_smtp)
    p_smtp.start()
    processes.append(p_smtp)

    time.sleep(2)

    try:
        start_gunicorn()
    except KeyboardInterrupt:
        signal_handler(None, None)