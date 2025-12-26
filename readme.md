# 📧 SilverMail - MultiPlatform

![Ubuntu 22.04](https://img.shields.io/badge/OS-Ubuntu%20Server%2022.04-orange?style=flat-square&logo=ubuntu)
![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python)
![Status](https://img.shields.io/badge/Status-Active-green?style=flat-square)

**SilverMail** adalah solusi *Temporary Email* (Email Sementara) yang mendukung banyak domain sekaligus. Dibangun dengan Python (Flask & aiosmtpd), sistem ini dirancang untuk ringan, cepat, dan mudah di-deploy.

---

## 📋 Prasyarat (Prerequisites)

Sebelum memulai instalasi, pastikan Anda telah memenuhi persyaratan berikut:

1.  **Server VPS/Dedicated:**
    * OS: Ubuntu Server 22.04 (Tested).
    * **IP Publik** statis.
    * Akses **Root** (Wajib, karena aplikasi menggunakan Port 25 dan 80).
2.  **Domain:**
    * Minimal 1 domain aktif.
    * Bisa menggunakan lebih dari 1 domain.

### ⚙️ Konfigurasi DNS (Wajib)
Agar email dapat diterima, Anda **harus** mengatur DNS record pada panel domain Anda sebagai berikut:

| Type | Host / Name | Value / Target | Priority | Keterangan |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `@` (Root) | `IP_PUBLIK_VPS_ANDA` | - | Mengarahkan domain ke server |
| **MX** | `@` (Root) | `nama-domain-anda.com` | `10` | Menangani rute email masuk |

> ⚠️ **Catatan:** Jika Anda menggunakan Cloudflare, pastikan status proxy (awan oranye) dimatikan untuk record MX (DNS Only).

---

## 🚀 Instalasi
Ikuti langkah-langkah berikut secara berurutan pada terminal Ubuntu Anda.

### 1. Update & Install Dependencies
Perbarui repository dan install paket dasar yang dibutuhkan.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip git -y
```

### 2. Clone Repository
Unduh source code SilverMail ke server Anda.

```bash
# Clone repository
git clone https://github.com/swwillbemine/SilverMail-MultiPlatform

# Masuk ke direktori project
cd SilverMail-MultiPlatform
```

### 3. Install Python Libraries
Install library Python yang dibutuhkan oleh aplikasi.

```bash
pip3 install flask aiosmtpd gunicorn
```
---

## 🔧 Konfigurasi
### 1. Setup Domain (`domain.json`)
Buat file konfigurasi untuk mendaftarkan domain-domain yang akan digunakan.

```bash
sudo nano domain.json
```
Isi dengan format JSON array (list). Ganti dengan nama domain Anda:
```bash
["domainanda.com", "domainkedua.xyz"]
```
Tekan `Ctrl+X`, lalu `Y`, dan `Enter` untuk menyimpan.

### 2. Setup Akun Admin (`config.json`)
Edit file konfigurasi untuk kredensial admin dan keamanan session.
```bash
sudo nano config.json
```
Isi dan sesuaikan data berikut
```bash
{
    "admin_username": "admin",
    "admin_password": "GantiPasswordSangatKuat123!",
    "secret_key": "masukkan_random_string_acak_disini"
}
```
Penting: Ganti `secret_key` dengan string acak yang panjang untuk keamanan session browser. Tekan `Ctrl+X`, lalu `Y`, dan `Enter` untuk menyimpan.
---

## 📦 Deployment (Systemd Service)
Aplikasi akan berjalan otomatis di latar belakang (background) dan auto-restart jika server reboot.

### 1. Buat Service File
```bash
sudo nano /etc/systemd/system/silvermail.service
```
Salin konfigurasi berikut ke dalamnya. *Pastikan path/lokasi direktori sesuai dengan tempat Anda melakukan clone (default: `/root/SilverMail-MultiPlatform`).*

```toml
[Unit]
Description=SilverMail All-in-One Service (SMTP + Web)
After=network.target

[Service]
# Root diperlukan karena kita bind Port 25 (SMTP) dan Port 80 (HTTP)
User=root
Group=root

# Working Directory (Sesuaikan jika lokasi clone berbeda)
WorkingDirectory=/root/SilverMail-MultiPlatform

# Jalankan Launcher
ExecStart=/usr/bin/python3 /root/SilverMail-MultiPlatform/launcher.py

# Restart otomatis jika crash
Restart=always
RestartSec=5

# Output log ke syslog
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=silvermail

[Install]
WantedBy=multi-user.target
```

### 2. Aktifkan Service
Jalankan perintah berikut untuk meregistrasi dan menyalakan service.
```bash
# Reload konfigurasi systemd
sudo systemctl daemon-reload

# Enable service agar jalan saat booting
sudo systemctl enable silvermail

# Jalankan service sekarang
sudo systemctl start silvermail
```

### 3.Cek Status
Pastikan service berjalan tanpa error (status harus `active (running)`).
```bash
sudo systemctl status silvermail
```
---

## 🔍 Troubleshooting
Jika status service gagal atau error, Anda bisa melihat log error dengan perintah:
```bash
journalctl -u silvermail -f
```
*Masalah Umum*
- *Port Conflict:* Pastikan tidak ada aplikasi lain (seperti Apache/Nginx atau Postfix) yang menggunakan Port 80 atau Port 25.
    - Cek port 80: `lsof -i :80`
    - Cek port 25: `lsof -i :25`
---
Created with ❤️ for Silver Wolf