"""
Blueprint: Auth (Login, Logout, Face Verification)
Mengelola autentikasi admin dengan dua langkah:
1. Username + Password
2. Verifikasi wajah via webcam/upload
"""

import os
import logging
import time

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
)

from utils.face_auth import verify_face, get_loaded_admins
from utils.sheets import log_login_attempt

logger = logging.getLogger(__name__)

# Definisi blueprint
auth_bp = Blueprint(
    "auth",
    __name__,
)

# ============================================
# Utilitas: Parsing admin credentials dari .env
# ============================================

def _get_admin_credentials():
    """
    Parse ADMIN_USERS dari .env.
    Format: 'username1:password1,username2:password2'

    Returns:
        dict: {username: password_plain_text}
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
            return jsonify({
                "success": False,
                "message": "Data tidak valid"
            }), 400

        username = data.get("username", "").strip().lower()
        password = data.get("password", "").strip()
        client_ip = request.remote_addr or "unknown"

        if not username or not password:
            return jsonify({
                "success": False,
                "message": "Username dan password wajib diisi"
            }), 400

        # Cek lockout
        lockout_status = _check_lockout(username)
        if lockout_status["locked"]:
            return jsonify({
                "success": False,
                "status": "LOCKED",
                "message": f"Akun terkunci. Coba lagi dalam "
                           f"{lockout_status['remaining_seconds']} detik.",
                "remaining_seconds": lockout_status["remaining_seconds"],
            }), 423

        # Validasi kredensial
        admin_creds = _get_admin_credentials()

        if username not in admin_creds:
            log_login_attempt(username, "FAILED_PASSWORD", "password_only", client_ip)
            return jsonify({
                "success": False,
                "status": "FAILED_PASSWORD",
                "message": "Username atau password salah"
            }), 401

        if admin_creds[username] != password:
            log_login_attempt(username, "FAILED_PASSWORD", "password_only", client_ip)
            return jsonify({
                "success": False,
                "status": "FAILED_PASSWORD",
                "message": "Username atau password salah"
            }), 401

        # Password valid — set pending session untuk face verification
        session["pending_user"] = username
        session["face_attempts"] = 0

        # Cek apakah ada foto referensi untuk user ini
        loaded_admins = get_loaded_admins()
        has_face_ref = username in loaded_admins

        if has_face_ref:
            logger.info(
                f"Password valid untuk '{username}', "
                "menunggu verifikasi wajah"
            )
            return jsonify({
                "success": True,
                "needs_face_verification": True,
                "message": "Password valid. Silakan verifikasi wajah."
            })
        else:
            # Tidak ada foto referensi — langsung login (password_only)
            session["logged_in"] = True
            session["username"] = username
            session.pop("pending_user", None)
            session.pop("face_attempts", None)

            log_login_attempt(username, "SUCCESS", "password_only", client_ip)
            logger.info(
                f"Login berhasil untuk '{username}' (tanpa face verification — "
                "foto referensi tidak tersedia)"
            )
            return jsonify({
                "success": True,
                "needs_face_verification": False,
                "message": "Login berhasil! Mengarahkan ke dashboard..."
            })

    except Exception as e:
        logger.error(f"Error saat proses login: {e}")
        return jsonify({
            "success": False,
            "message": "Terjadi kesalahan server"
        }), 500


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
            return jsonify({
                "success": False,
                "match": False,
                "message": "Terlalu cepat. Tunggu beberapa detik sebelum mencoba lagi."
            }), 429
        session["last_face_request"] = now

        # Cek apakah ada pending user di session
        pending_user = session.get("pending_user")
        if not pending_user:
            return jsonify({
                "success": False,
                "message": "Sesi tidak valid. Silakan login ulang."
            }), 401

        client_ip = request.remote_addr or "unknown"
        max_attempts = int(os.getenv("MAX_FACE_ATTEMPTS", "3"))

        # Cek lockout
        lockout_status = _check_lockout(pending_user)
        if lockout_status["locked"]:
            return jsonify({
                "success": False,
                "status": "LOCKED",
                "match": False,
                "message": f"Akun terkunci. Coba lagi dalam "
                           f"{lockout_status['remaining_seconds']} detik.",
                "remaining_seconds": lockout_status["remaining_seconds"],
            }), 423

        data = request.get_json()
        if not data or not data.get("image"):
            return jsonify({
                "success": False,
                "match": False,
                "message": "Data gambar tidak ditemukan"
            }), 400

        image_base64 = data["image"]

        # Jalankan verifikasi wajah
        result = verify_face(pending_user, image_base64)

        if result["match"]:
            # Wajah cocok — login berhasil
            session["logged_in"] = True
            session["username"] = pending_user
            session.pop("pending_user", None)
            session.pop("face_attempts", None)

            log_login_attempt(
                pending_user, "SUCCESS", "password+face", client_ip
            )
            logger.info(f"Login berhasil untuk '{pending_user}' via face verification")

            return jsonify({
                "success": True,
                "match": True,
                "message": "Verifikasi wajah berhasil! Mengarahkan ke dashboard...",
                "confidence": result.get("confidence", 0),
            })

        else:
            # Wajah tidak cocok — increment attempts
            face_attempts = session.get("face_attempts", 0) + 1
            session["face_attempts"] = face_attempts

            attempts_remaining = max_attempts - face_attempts

            if attempts_remaining <= 0:
                # Lockout — catat waktu lockout
                lockout_minutes = int(os.getenv("LOCKOUT_MINUTES", "5"))
                session["lockout_until"] = time.time() + (lockout_minutes * 60)
                session["lockout_user"] = pending_user
                session.pop("pending_user", None)
                session.pop("face_attempts", None)

                log_login_attempt(
                    pending_user, "FAILED_FACE", "password+face", client_ip
                )
                logger.warning(
                    f"Akun '{pending_user}' terkunci selama {lockout_minutes} "
                    "menit setelah 3x gagal verifikasi wajah"
                )

                return jsonify({
                    "success": False,
                    "match": False,
                    "status": "LOCKED",
                    "message": f"Verifikasi wajah gagal {max_attempts}x berturut-turut. "
                               f"Akun terkunci selama {lockout_minutes} menit.",
                    "remaining_seconds": lockout_minutes * 60,
                }), 423

            else:
                log_login_attempt(
                    pending_user, "FAILED_FACE", "password+face", client_ip
                )
                logger.warning(
                    f"Verifikasi wajah gagal untuk '{pending_user}' "
                    f"(percobaan {face_attempts}/{max_attempts})"
                )

                return jsonify({
                    "success": False,
                    "match": False,
                    "message": result.get("message", "Wajah tidak dikenali."),
                    "attempts_remaining": attempts_remaining,
                    "confidence": result.get("confidence", 1.0),
                })

    except Exception as e:
        logger.error(f"Error saat verifikasi wajah: {e}")
        return jsonify({
            "success": False,
            "match": False,
            "message": "Terjadi kesalahan server saat verifikasi wajah."
        }), 500


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
# Helper: Lockout Management
# ============================================

def _check_lockout(username):
    """
    Cek apakah akun admin sedang terkunci (lockout).

    Args:
        username: Username yang akan dicek.

    Returns:
        dict: {
            'locked': bool,
            'remaining_seconds': int (0 jika tidak terkunci)
        }
    """
    lockout_until = session.get("lockout_until", 0)
    lockout_user = session.get("lockout_user", "")

    if lockout_user == username and lockout_until > time.time():
        remaining = int(lockout_until - time.time())
        return {"locked": True, "remaining_seconds": remaining}

    # Lockout sudah expired — bersihkan
    if lockout_user == username:
        session.pop("lockout_until", None)
        session.pop("lockout_user", None)

    return {"locked": False, "remaining_seconds": 0}
