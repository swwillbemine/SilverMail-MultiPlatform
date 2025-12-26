1. nano /etc/systemd/system/silvermail.service
2. isi dengan

[Unit]
Description=SilverMail All-in-One Service (SMTP + Web)
After=network.target

[Service]
# Root diperlukan karena kita bind Port 25 dan Port 80
User=root
Group=root

# Working Directory (Sesuaikan dengan lokasi Anda)
WorkingDirectory=/root/SilverMail-MultiDomain

# Jalankan Launcher
ExecStart=/usr/bin/python3 /root/SilverMail-MultiDomain/launcher.py

# Restart otomatis jika crash
Restart=always
RestartSec=5

# Output log ke syslog
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=silvermail

[Install]
WantedBy=multi-user.target

3. sudo systemctl daemon-reload

8. sudo systemctl enable silvermail
9. sudo systemctl start silvermail

10. sudo systemctl status silvermail