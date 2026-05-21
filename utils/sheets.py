"""
Modul helper untuk integrasi Google Sheets.
Menyediakan fungsi CRUD ke spreadsheet via gspread.
"""

import os
import logging
import time

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# === Cache sederhana dengan TTL (Time-To-Live) ===
# Format: {sheet_name: (timestamp, data)}
_cache = {}
_CACHE_TTL = 60  # Detik — jangan fetch ulang jika data masih segar

# Scope yang diperlukan untuk Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    """
    Autentikasi ke Google Sheets menggunakan service account.
    Returns: gspread.Client yang sudah terautentikasi.
    """
    try:
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        client = gspread.authorize(credentials)
        logger.info("Berhasil terhubung ke Google Sheets API")
        return client
    except FileNotFoundError:
        logger.error(f"File kredensial tidak ditemukan: {creds_path}")
        raise
    except Exception as e:
        logger.error(f"Gagal autentikasi Google Sheets: {e}")
        raise


def get_sheet(sheet_name):
    """
    Membuka worksheet tertentu dari spreadsheet yang dikonfigurasi.
    Args:
        sheet_name: Nama worksheet (tab) yang akan dibuka.
    Returns: gspread.Worksheet
    """
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID tidak ditemukan di .env")

        client = get_client()
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        logger.info(f"Berhasil membuka worksheet: {sheet_name}")
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Worksheet '{sheet_name}' tidak ditemukan di spreadsheet")
        raise
    except Exception as e:
        logger.error(f"Gagal membuka worksheet '{sheet_name}': {e}")
        raise


def append_row(sheet_name, data):
    """
    Menambahkan satu baris data ke worksheet.
    Args:
        sheet_name: Nama worksheet target.
        data: List berisi nilai-nilai kolom (urut).
    Returns: dict hasil operasi dari gspread.
    """
    try:
        worksheet = get_sheet(sheet_name)
        result = worksheet.append_row(data, value_input_option="USER_ENTERED")
        logger.info(f"Baris berhasil ditambahkan ke '{sheet_name}': {data}")

        # Invalidate cache untuk sheet yang baru ditambah data
        if sheet_name in _cache:
            del _cache[sheet_name]
            logger.info(f"Cache untuk '{sheet_name}' di-invalidate setelah append")

        return result
    except Exception as e:
        logger.error(f"Gagal menambahkan baris ke '{sheet_name}': {e}")
        raise


def get_all_records(sheet_name):
    """
    Mengambil semua data dari worksheet sebagai list of dicts.
    Baris pertama digunakan sebagai header/key.
    Args:
        sheet_name: Nama worksheet.
    Returns: List[dict] semua record.
    """
    try:
        # Cek cache terlebih dahulu
        now = time.time()
        if sheet_name in _cache:
            cached_time, cached_data = _cache[sheet_name]
            if now - cached_time < _CACHE_TTL:
                logger.info(
                    f"Cache hit untuk '{sheet_name}' "
                    f"({len(cached_data)} record, sisa {int(_CACHE_TTL - (now - cached_time))}s)"
                )
                return cached_data

        # Cache miss atau expired — fetch dari Google Sheets
        worksheet = get_sheet(sheet_name)
        records = worksheet.get_all_records()
        logger.info(f"Berhasil mengambil {len(records)} record dari '{sheet_name}' (fresh fetch)")

        # Simpan ke cache
        _cache[sheet_name] = (now, records)

        return records
    except Exception as e:
        logger.error(f"Gagal mengambil data dari '{sheet_name}': {e}")
        raise


def get_karyawan_list():
    """
    Mengambil daftar nama karyawan dari sheet 'Karyawan'.
    Returns: List[str] nama-nama karyawan.
    """
    try:
        records = get_all_records("Karyawan")
        nama_list = [r.get("Nama", "") for r in records if r.get("Nama")]
        logger.info(f"Ditemukan {len(nama_list)} karyawan")
        return nama_list
    except Exception as e:
        logger.error(f"Gagal mengambil daftar karyawan: {e}")
        return []


def ensure_login_log_sheet():
    """
    Memastikan tab 'Login_Log' ada di spreadsheet.
    Jika belum ada, buat tab baru dengan header row.
    Columns: Timestamp | Username | Status | Method | IP
    """
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID tidak ditemukan di .env")

        client = get_client()
        spreadsheet = client.open_by_key(sheet_id)

        # Cek apakah worksheet sudah ada
        try:
            spreadsheet.worksheet("Login_Log")
            logger.info("Tab 'Login_Log' sudah ada")
        except gspread.exceptions.WorksheetNotFound:
            # Buat worksheet baru dengan header
            worksheet = spreadsheet.add_worksheet(
                title="Login_Log", rows=1000, cols=5
            )
            headers = ["Timestamp", "Username", "Status", "Method", "IP"]
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
            logger.info("Tab 'Login_Log' berhasil dibuat dengan header")

    except Exception as e:
        logger.error(f"Gagal memastikan tab Login_Log: {e}")


def log_login_attempt(username, status, method, ip):
    """
    Mencatat percobaan login ke tab 'Login_Log' di Google Sheets.

    Args:
        username: Username yang mencoba login.
        status: Status percobaan — 'SUCCESS', 'FAILED_PASSWORD', 'FAILED_FACE'.
        method: Metode login — 'password+face', 'password_only'.
        ip: Alamat IP client.
    """
    from datetime import datetime

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [timestamp, username, status, method, ip]
        append_row("Login_Log", row_data)
        logger.info(
            f"Login attempt dicatat: {username} | {status} | {method} | {ip}"
        )
    except Exception as e:
        logger.error(f"Gagal mencatat login attempt ke Login_Log: {e}")

