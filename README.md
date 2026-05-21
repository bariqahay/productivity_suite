# Productivity Suite — PT Telkom Indonesia (Enterprise Division)

Aplikasi web multi-halaman berbasis **Flask** untuk manajemen kehadiran, dashboard analytics, dan generator artikel AI. Dibangun sebagai proyek magang di PT Telkom Indonesia — Enterprise Division, Medan.

## Fitur Utama

| Halaman       | Fitur                                                                                           |
|---------------|-------------------------------------------------------------------------------------------------|
| **Absensi**   | Form kehadiran, notifikasi Telegram otomatis, audit log real-time                               |
| **Dashboard** | Chart analytics (bar, donut, line), K-Means clustering, rekap per karyawan, export Excel        |
| **Artikel**   | AI article generator (Groq/LLaMA 3.3 70B), word cloud, download .docx                          |
| **Login**     | Autentikasi 2 langkah: password + face verification via webcam                                  |

## Mapping Mata Kuliah ke Fitur

| Mata Kuliah | Justifikasi |
|---|---|
| **Internet of Things** | Integrasi Telegram Bot API sebagai kanal notifikasi real-time saat karyawan melakukan absensi — mensimulasikan komunikasi perangkat-ke-pengguna dalam ekosistem IoT |
| **Forensik Digital** | Pencatatan login attempt (timestamp, IP, status, metode) ke sheet `Login_Log` dan mekanisme lockout berfungsi sebagai **audit trail** untuk analisis forensik keamanan |
| **Pengolahan Citra Digital** | Modul `face_auth.py` menggunakan `face_recognition` (128D face encoding) dan fallback **Haar Cascade + histogram correlation** di OpenCV untuk verifikasi identitas berbasis citra wajah |
| **Big Data** | Google Sheets sebagai data store terdistribusi, caching TTL untuk efisiensi query, serta pengolahan batch data kehadiran dengan Pandas (filtering, grouping, aggregation) |
| **Penambangan Data** | Implementasi **K-Means Clustering** dengan `StandardScaler` normalisasi untuk mengelompokkan pola kehadiran karyawan menjadi 3 kluster (Konsisten, Sering Izin, Tidak Konsisten) |

## Struktur Folder

```
projek_magang/
├── app.py                      # Entry point — Flask application factory
├── requirements.txt            # Daftar dependensi Python
├── .env                        # Environment variables (TIDAK di-commit)
├── credentials.json            # Google Service Account key (TIDAK di-commit)
├── DESIGN.md                   # Dokumentasi design system
│
├── blueprints/                 # Modul halaman (Flask Blueprints)
│   ├── __init__.py
│   ├── auth.py                 # Login, logout, face verification
│   ├── absensi.py              # Form kehadiran & audit log
│   ├── dashboard.py            # Analytics & K-Means clustering
│   └── artikel.py              # AI article generator
│
├── utils/                      # Modul utilitas backend
│   ├── __init__.py
│   ├── sheets.py               # Google Sheets helper (dengan TTL cache)
│   ├── telegram.py             # Telegram Bot notifikasi
│   ├── face_auth.py            # Face encoding & verification
│   └── image_gen.py            # Word cloud generator
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Layout dasar (sidebar + content)
│   ├── login.html              # Halaman login (standalone)
│   ├── absensi.html
│   ├── dashboard.html
│   └── artikel.html
│
└── static/
    ├── css/style.css           # Design system CSS
    ├── js/main.js              # JavaScript (vanilla JS)
    └── assets/
        ├── telkom_logo.png     # Logo Telkom
        └── admin_faces/        # Foto referensi admin (TIDAK di-commit)
```

## Cara Setup

### 1. Clone & Install Dependencies

```bash
git clone <repository-url>
cd projek_magang
pip install -r requirements.txt
```

> **Catatan**: Library `face_recognition` membutuhkan `dlib` yang memerlukan CMake dan compiler C++. Jika instalasi gagal, aplikasi tetap bisa berjalan dengan fallback OpenCV (Haar Cascade).

### 2. Konfigurasi `.env`

Buat file `.env` di root project dengan isi berikut:

```env
# Google Sheets
GOOGLE_SHEET_ID=<spreadsheet_id>
GOOGLE_CREDENTIALS_PATH=credentials.json

# Telegram Bot
TELEGRAM_BOT_TOKEN=<bot_token>
TELEGRAM_CHAT_ID=<chat_id>

# Groq AI (untuk Artikel Generator)
GROQ_API_KEY=<groq_api_key>

# Info Kantor
OFFICE_LOCATION=Telkom Enterprise, Medan
ANNOUNCEMENT_TEXT=Harap melakukan absensi sebelum 09.00 WIB.
ANNOUNCEMENT_DATE=20 Mei 2026

# Admin Login & Face Verification
ADMIN_USERS=username1:password1,username2:password2
FACE_TOLERANCE=0.5
ADMIN_FACES_DIR=static/assets/admin_faces
MAX_FACE_ATTEMPTS=3
LOCKOUT_MINUTES=5

# Flask
SECRET_KEY=<random_secret_key>
```

### 3. Google Sheets Credentials

1. Buat project di [Google Cloud Console](https://console.cloud.google.com/)
2. Aktifkan Google Sheets API & Google Drive API
3. Buat Service Account dan download key JSON
4. Simpan sebagai `credentials.json` di root project
5. Share spreadsheet ke email service account

### 4. Foto Referensi Admin (Face Verification)

Simpan foto wajah admin di `static/assets/admin_faces/`:
- Nama file = username (contoh: `rifki.jpg` untuk username `rifki`)
- Format: `.jpg`, `.jpeg`, `.png`
- Pastikan wajah terlihat jelas dan pencahayaan cukup
- Foto akan di-encode saat aplikasi start

### 5. Menjalankan Aplikasi

```bash
python app.py
```

Aplikasi berjalan di `http://localhost:5000`.

## Teknologi

- **Backend**: Python 3.10+, Flask 3.x
- **Frontend**: HTML5, Vanilla CSS, Vanilla JavaScript, Chart.js
- **Database**: Google Sheets (via gspread)
- **AI**: Groq API (LLaMA 3.3 70B)
- **CV**: face_recognition + OpenCV
- **Notifikasi**: Telegram Bot API
- **Analytics**: pandas, scikit-learn (K-Means)
