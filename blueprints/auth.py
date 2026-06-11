"""
Blueprint: Auth (Login, Logout, Face Verification)
Mengelola autentikasi admin dengan dua langkah:
1. Username + Password
2. Verifikasi wajah via webcam/upload
"""

import logging
import os
import time

import bcrypt
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from utils.face_auth import get_loaded_admins, verify_face
from utils.sheets import load_lockout_state, log_login_attempt, save_lockout_state

logger = logging.getLogger(__name__)

# Definisi blueprint
auth_bp = Blueprint(
    "auth",
    __name__,
)

# ============================================
# Utilitas: Parsing admin credentials dari .env
# ============================================


def _is_bcrypt_hash(value: str) -> bool:
    """Return True if value is a bcrypt hash (not plain-text)."""
    return value.startswith(("$2b$", "$2a$", "$2y$"))


def _get_admin_credentials():
    """
    Parse ADMIN_USERS dari .env.
    Format: 'username1:bcrypt_hash1,username2:bcrypt_hash2'
    Legacy plain-text passwords are still accepted here and compared
    safely — run migrate_passwords.py to upgrade them to hashes.

    Returns:
        dict: {username: password_hash_or_plain}
    """
    admin_str = os.getenv("ADMIN_USERS", "")
    credentials = {}

    if not admin_str:
        logger.warning("ADMIN_USERS tidak ditemukan di .env")
        return credentials

    for pair in admin_str.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        username, password = pair.split(":", 1)
        credentials[username.strip().lower()] = password.strip()

    return credentials


def _check_password(plain: str, stored: str) -> bool:
    """
    Verify a password against a stored bcrypt hash or (legacy) plain text.
    Always runs in constant time to prevent timing attacks.
    """
    if _is_bcrypt_hash(stored):
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    # Legacy plain-text fallback — log a warning so admins know to migrate
    logger.warning(
        "Plain-text password detected in ADMIN_USERS. "
        "Run migrate_passwords.py to upgrade to bcrypt hashes."
    )
    return plain == stored


# ============================================
# Routes
# ============================================


@auth_bp.route("/login")
def login_page():
    """
    Halaman login admin.
    Jika sudah login, redirect ke halaman utama.
    """
    if session.get("logged_in"):
        return redirect(url_for("absensi.index"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_submit():
    """
    Endpoint untuk validasi username + password.
    Jika valid, set session pending dan minta verifikasi wajah.

    Request JSON: { username, password }
    Response JSON:
        - 200 { needs_face_verification: true } → lanjut ke face verify
        - 401 { status: 'FAILED_PASSWORD', message: ... }
        - 423 { status: 'LOCKED', message: ..., remaining_seconds: ... }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Data tidak valid"}), 400

        username = data.get("username", "").strip().lower()
        password = data.get("password", "").strip()
        client_ip = request.remote_addr or "unknown"

        if not username or not password:
            return jsonify(
                {"success": False, "message": "Username dan password wajib diisi"}
            ), 400

        # Cek lockout
        lockout_status = _check_lockout(username)
        if lockout_status["locked"]:
            return jsonify(
                {
                    "success": False,
                    "status": "LOCKED",
                    "message": f"Akun terkunci. Coba lagi dalam "
                    f"{lockout_status['remaining_seconds']} detik.",
                    "remaining_seconds": lockout_status["remaining_seconds"],
                }
            ), 423

        # Validasi kredensial
        admin_creds = _get_admin_credentials()

        if username not in admin_creds:
            log_login_attempt(username, "FAILED_PASSWORD", "password_only", client_ip)
            _record_failed_attempt(username)
            return jsonify(
                {
                    "success": False,
                    "status": "FAILED_PASSWORD",
                    "message": "Username atau password salah",
                }
            ), 401

        if not _check_password(password, admin_creds[username]):
            log_login_attempt(username, "FAILED_PASSWORD", "password_only", client_ip)
            _record_failed_attempt(username)
            return jsonify(
                {
                    "success": False,
                    "status": "FAILED_PASSWORD",
                    "message": "Username atau password salah",
                }
            ), 401

        # Password valid — set pending session untuk face verification
        session["pending_user"] = username
        session["face_attempts"] = 0

        # Cek apakah ada foto referensi untuk user ini
        loaded_admins = get_loaded_admins()
        has_face_ref = username in loaded_admins

        if has_face_ref:
            logger.info(f"Password valid untuk '{username}', menunggu verifikasi wajah")
            return jsonify(
                {
                    "success": True,
                    "needs_face_verification": True,
                    "message": "Password valid. Silakan verifikasi wajah.",
                }
            )
        else:
            # Tidak ada foto referensi — langsung login (password_only)
            session["logged_in"] = True
            session["username"] = username
            session.pop("pending_user", None)
            session.pop("face_attempts", None)

            _reset_lockout(username)
            log_login_attempt(username, "SUCCESS", "password_only", client_ip)
            logger.info(
                f"Login berhasil untuk '{username}' (tanpa face verification — "
                "foto referensi tidak tersedia)"
            )
            return jsonify(
                {
                    "success": True,
                    "needs_face_verification": False,
                    "message": "Login berhasil! Mengarahkan ke dashboard...",
                }
            )

    except Exception as e:
        logger.error(f"Error saat proses login: {e}")
        return jsonify({"success": False, "message": "Terjadi kesalahan server"}), 500


@auth_bp.route("/verify-face", methods=["POST"])
def verify_face_endpoint():
    """
    Endpoint untuk verifikasi wajah admin.
    Hanya bisa dipanggil setelah password valid (ada pending_user di session).
    Rate limit: maksimum 1 request per 2 detik per session.

    Request JSON: { image: base64_string }
    Response JSON:
        - 200 { match: true, message: ... }
        - 200 { match: false, message: ..., attempts_remaining: ... }
        - 423 { status: 'LOCKED', message: ..., remaining_seconds: ... }
        - 429 { message: ... } jika rate limit tercapai
    """
    try:
        # Rate limiting: 1 request per 2 detik
        now = time.time()
        last_request = session.get("last_face_request", 0)
        if now - last_request < 2:
            return jsonify(
                {
                    "success": False,
                    "match": False,
                    "message": "Terlalu cepat. Tunggu beberapa detik sebelum mencoba lagi.",
                }
            ), 429
        session["last_face_request"] = now

        # Cek apakah ada pending user di session
        pending_user = session.get("pending_user")
        if not pending_user:
            return jsonify(
                {"success": False, "message": "Sesi tidak valid. Silakan login ulang."}
            ), 401

        client_ip = request.remote_addr or "unknown"
        max_attempts = int(os.getenv("MAX_FACE_ATTEMPTS", "3"))

        # Cek lockout
        lockout_status = _check_lockout(pending_user)
        if lockout_status["locked"]:
            return jsonify(
                {
                    "success": False,
                    "status": "LOCKED",
                    "match": False,
                    "message": f"Akun terkunci. Coba lagi dalam "
                    f"{lockout_status['remaining_seconds']} detik.",
                    "remaining_seconds": lockout_status["remaining_seconds"],
                }
            ), 423

        data = request.get_json()
        if not data or not data.get("image"):
            return jsonify(
                {
                    "success": False,
                    "match": False,
                    "message": "Data gambar tidak ditemukan",
                }
            ), 400

        image_base64 = data["image"]

        # Jalankan verifikasi wajah
        result = verify_face(pending_user, image_base64)

        face_method = result.get(
            "method", "face_recognition"
        )  # 'face_recognition' | 'opencv_fallback'

        if result["match"]:
            # Wajah cocok — login berhasil
            session["logged_in"] = True
            session["username"] = pending_user
            session.pop("pending_user", None)
            session.pop("face_attempts", None)

            # Reset persistent lockout counter
            _reset_lockout(pending_user)

            log_method = f"password+face({face_method})"
            log_login_attempt(pending_user, "SUCCESS", log_method, client_ip)
            logger.info(
                f"Login berhasil untuk '{pending_user}' via face verification "
                f"(method={face_method})"
            )

            return jsonify(
                {
                    "success": True,
                    "match": True,
                    "message": "Verifikasi wajah berhasil! Mengarahkan ke dashboard...",
                    "confidence": result.get("confidence", 0),
                    "face_method": face_method,
                }
            )

        else:
            # Wajah tidak cocok — record attempt and check lockout
            _record_failed_attempt(pending_user)
            log_login_attempt(pending_user, "FAILED_FACE", "password+face", client_ip)

            # Re-load state to check if now locked
            new_lockout = _check_lockout(pending_user)
            if new_lockout["locked"]:
                lockout_minutes = int(os.getenv("LOCKOUT_MINUTES", "5"))
                session.pop("pending_user", None)
                session.pop("face_attempts", None)

                return jsonify(
                    {
                        "success": False,
                        "match": False,
                        "status": "LOCKED",
                        "message": f"Verifikasi wajah gagal {max_attempts}x berturut-turut. "
                        f"Akun terkunci selama {lockout_minutes} menit.",
                        "remaining_seconds": new_lockout["remaining_seconds"],
                    }
                ), 423

            else:
                # Load current count to show remaining attempts
                state = load_lockout_state(pending_user)
                attempts_so_far = state["attempt_count"]
                attempts_remaining = max(0, max_attempts - attempts_so_far)

                logger.warning(
                    f"Verifikasi wajah gagal untuk '{pending_user}' "
                    f"(percobaan {attempts_so_far}/{max_attempts})"
                )

                return jsonify(
                    {
                        "success": False,
                        "match": False,
                        "message": result.get("message", "Wajah tidak dikenali."),
                        "attempts_remaining": attempts_remaining,
                        "confidence": result.get("confidence", 1.0),
                        "face_method": face_method,
                    }
                )

    except Exception as e:
        logger.error(f"Error saat verifikasi wajah: {e}")
        return jsonify(
            {
                "success": False,
                "match": False,
                "message": "Terjadi kesalahan server saat verifikasi wajah.",
            }
        ), 500


@auth_bp.route("/logout")
def logout():
    """
    Logout — hapus semua session data, redirect ke login.
    """
    username = session.get("username", "unknown")
    session.clear()
    logger.info(f"User '{username}' berhasil logout")
    return redirect(url_for("auth.login_page"))


# ============================================
# Helper: Lockout Management (persisted to Lockout_State sheet)
# ============================================


def _check_lockout(username: str) -> dict:
    """
    Cek apakah akun admin sedang terkunci.
    State diambil dari Google Sheets (survive server restart).

    Returns:
        dict: {'locked': bool, 'remaining_seconds': int}
    """
    state = load_lockout_state(username)
    locked_until = state["locked_until"]

    if locked_until > time.time():
        remaining = int(locked_until - time.time())
        return {"locked": True, "remaining_seconds": remaining}

    return {"locked": False, "remaining_seconds": 0}


def _record_failed_attempt(username: str) -> None:
    """
    Increment the failed-attempt counter and persist to sheet.
    Triggers lockout if MAX_FACE_ATTEMPTS is reached.
    """
    state = load_lockout_state(username)
    new_count = state["attempt_count"] + 1
    now = time.time()
    max_attempts = int(os.getenv("MAX_FACE_ATTEMPTS", "3"))
    lockout_minutes = int(os.getenv("LOCKOUT_MINUTES", "5"))

    locked_until = 0.0
    if new_count >= max_attempts:
        locked_until = now + lockout_minutes * 60
        logger.warning(
            f"Akun '{username}' dikunci sampai "
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(locked_until))}"
        )

    save_lockout_state(username, new_count, now, locked_until)


def _reset_lockout(username: str) -> None:
    """Clear lockout state after a successful login."""
    save_lockout_state(username, 0, time.time(), 0.0)
