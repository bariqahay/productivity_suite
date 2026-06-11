"""
Modul helper untuk integrasi Google Sheets.
Menyediakan fungsi CRUD ke spreadsheet via gspread.

Writes are always non-blocking: append_row() enqueues the work and returns
immediately. A background daemon thread drains the queue and retries on
HTTP 429 (quota exceeded) with exponential back-off.

Call start_write_worker() once inside create_app() to start the worker.
"""

import logging
import os
import queue
import threading
import time

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# === Cache sederhana dengan TTL (Time-To-Live) ===
# Format: {sheet_name: (timestamp, data)}
_cache = {}
_CACHE_TTL = 60  # Detik — jangan fetch ulang jika data masih segar

# === Write queue ===
# Each item: (sheet_name, row_data)
_write_queue: queue.Queue = queue.Queue()
_WORKER_STARTED = False
_WORKER_LOCK = threading.Lock()

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


def _do_append_row(sheet_name, data, attempt=1, max_attempts=6):
    """
    Internal: perform the actual Sheets API write.
    Retries up to max_attempts times with exponential back-off on 429.
    """
    delay = 2  # Initial back-off seconds
    for attempt in range(1, max_attempts + 1):
        try:
            worksheet = get_sheet(sheet_name)
            worksheet.append_row(data, value_input_option="USER_ENTERED")
            logger.info(f"[queue] Baris ditambahkan ke '{sheet_name}': {data}")

            # Invalidate cache
            if sheet_name in _cache:
                del _cache[sheet_name]
                logger.debug(f"Cache '{sheet_name}' di-invalidate setelah append")
            return  # success

        except gspread.exceptions.APIError as e:
            status = getattr(e.response, "status_code", None)
            if status == 429 and attempt < max_attempts:
                logger.warning(
                    f"[queue] Rate-limited (429) saat menulis ke '{sheet_name}'. "
                    f"Retry {attempt}/{max_attempts} dalam {delay}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, 64)  # cap at 64 s
            else:
                logger.error(
                    f"[queue] Gagal menulis ke '{sheet_name}' setelah "
                    f"{attempt} percobaan: {e}"
                )
                return
        except Exception as e:
            logger.error(
                f"[queue] Error tidak terduga saat menulis ke '{sheet_name}': {e}"
            )
            return


def _write_worker():
    """Background thread that drains _write_queue and persists each row."""
    logger.info("[queue] Write worker started")
    while True:
        try:
            sheet_name, data = _write_queue.get(block=True, timeout=5)
            _do_append_row(sheet_name, data)
            _write_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"[queue] Worker unexpected error: {e}")


def start_write_worker():
    """
    Start the singleton background write worker thread.
    Must be called once inside create_app() (within app context).
    """
    global _WORKER_STARTED
    with _WORKER_LOCK:
        if _WORKER_STARTED:
            return
        t = threading.Thread(
            target=_write_worker, daemon=True, name="sheets-write-worker"
        )
        t.start()
        _WORKER_STARTED = True
        logger.info("[queue] Sheets write worker thread started")


def append_row(sheet_name, data):
    """
    Enqueue a row to be appended to a worksheet (non-blocking).
    The background worker handles the actual API call with retry.

    Args:
        sheet_name: Nama worksheet target.
        data: List berisi nilai-nilai kolom (urut).
    """
    _write_queue.put((sheet_name, data))
    logger.debug(f"[queue] Enqueued row untuk '{sheet_name}': {data}")


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
        logger.info(
            f"Berhasil mengambil {len(records)} record dari '{sheet_name}' (fresh fetch)"
        )

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
    Memastikan tab 'Login_Log' dan 'Lockout_State' ada di spreadsheet.

    Login_Log columns  : Timestamp | Username | Status | Method | IP
    Lockout_State cols : Username | AttemptCount | LastAttempt | LockedUntil
    """
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID tidak ditemukan di .env")

        client = get_client()
        spreadsheet = client.open_by_key(sheet_id)

        # --- Login_Log ---
        try:
            spreadsheet.worksheet("Login_Log")
            logger.info("Tab 'Login_Log' sudah ada")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="Login_Log", rows=1000, cols=5)
            headers = ["Timestamp", "Username", "Status", "Method", "IP"]
            worksheet.append_row(headers, value_input_option="USER_ENTERED")
            logger.info("Tab 'Login_Log' berhasil dibuat dengan header")

        # --- Lockout_State ---
        try:
            spreadsheet.worksheet("Lockout_State")
            logger.info("Tab 'Lockout_State' sudah ada")
        except gspread.exceptions.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title="Lockout_State", rows=200, cols=4)
            ws.append_row(
                ["Username", "AttemptCount", "LastAttempt", "LockedUntil"],
                value_input_option="USER_ENTERED",
            )
            logger.info("Tab 'Lockout_State' berhasil dibuat")

    except Exception as e:
        logger.error(f"Gagal memastikan tab Login_Log/Lockout_State: {e}")


# ============================================================
# Lockout state persistence
# ============================================================


def load_lockout_state(username: str) -> dict:
    """
    Load persisted lockout state for a username from the Lockout_State sheet.

    Returns:
        dict: {
            'attempt_count': int,
            'last_attempt': float (unix timestamp, 0 if none),
            'locked_until': float (unix timestamp, 0 if not locked),
        }
    """
    default = {"attempt_count": 0, "last_attempt": 0.0, "locked_until": 0.0}
    try:
        ws = get_sheet("Lockout_State")
        records = ws.get_all_records()  # [{Username, AttemptCount, ...}, ...]
        for row in records:
            if str(row.get("Username", "")).lower() == username.lower():
                return {
                    "attempt_count": int(row.get("AttemptCount", 0) or 0),
                    "last_attempt": float(row.get("LastAttempt", 0) or 0),
                    "locked_until": float(row.get("LockedUntil", 0) or 0),
                }
        return default
    except Exception as e:
        logger.error(f"Gagal membaca lockout state untuk '{username}': {e}")
        return default


def save_lockout_state(
    username: str, attempt_count: int, last_attempt: float, locked_until: float
) -> None:
    """
    Upsert the lockout row for a username in the Lockout_State sheet.
    Performed synchronously (no queue) because we need the write to
    survive a server restart — this is called sparingly (only on failed
    attempts / lockout events).
    """
    try:
        ws = get_sheet("Lockout_State")
        records = ws.get_all_records()

        row_data = [username, attempt_count, last_attempt, locked_until]

        # Find existing row index (1-based; +2 because header is row 1)
        for idx, row in enumerate(records):
            if str(row.get("Username", "")).lower() == username.lower():
                sheet_row = idx + 2  # +1 header, +1 for 1-based index
                ws.update(f"A{sheet_row}:D{sheet_row}", [row_data])
                logger.info(f"Lockout state updated untuk '{username}': {row_data}")
                return

        # No existing row — append new
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        logger.info(f"Lockout state created untuk '{username}': {row_data}")

    except Exception as e:
        logger.error(f"Gagal menyimpan lockout state untuk '{username}': {e}")


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
        logger.info(f"Login attempt dicatat: {username} | {status} | {method} | {ip}")
    except Exception as e:
        logger.error(f"Gagal mencatat login attempt ke Login_Log: {e}")
