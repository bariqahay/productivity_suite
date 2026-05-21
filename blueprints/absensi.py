"""
Blueprint: Absensi
Mengelola form kehadiran, submit ke Google Sheets,
kirim notifikasi Telegram, dan tampilkan audit log.
"""

import os
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify

from utils.sheets import get_karyawan_list, append_row, get_all_records
from utils.telegram import send_notification

logger = logging.getLogger(__name__)

# Definisi blueprint
absensi_bp = Blueprint(
    "absensi",
    __name__,
    url_prefix="/absensi",
)


@absensi_bp.route("/")
def index():
    """
    Halaman utama Absensi.
    Menampilkan form kehadiran dan tabel audit log.
    """
    # Ambil daftar karyawan untuk dropdown
    karyawan_list = []
    try:
        karyawan_list = get_karyawan_list()
    except Exception as e:
        logger.error(f"Gagal mengambil daftar karyawan: {e}")

    # Ambil riwayat kehadiran terbaru (20 record terakhir)
    audit_log = []
    try:
        all_records = get_all_records("Absensi")
        # Ambil 20 record terakhir, urutan terbaru di atas
        audit_log = list(reversed(all_records[-20:]))
    except Exception as e:
        logger.error(f"Gagal mengambil audit log: {e}")

    # Ambil teks pengumuman dan tanggal dari .env
    announcement_text = os.getenv("ANNOUNCEMENT_TEXT", "")
    announcement_date = os.getenv("ANNOUNCEMENT_DATE", "")

    return render_template(
        "absensi.html",
        karyawan_list=karyawan_list,
        audit_log=audit_log,
        announcement_text=announcement_text,
        announcement_date=announcement_date,
    )


@absensi_bp.route("/submit", methods=["POST"])
def submit():
    """
    Endpoint untuk mencatat kehadiran.
    Menerima JSON: { nama, status, catatan }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "Data tidak valid"}), 400

        nama = data.get("nama", "").strip()
        status = data.get("status", "").strip()
        catatan = data.get("catatan", "").strip()

        # Validasi wajib
        if not nama or not status:
            return jsonify({"success": False, "message": "Nama dan status wajib diisi"}), 400

        # Validasi status yang diperbolehkan
        allowed_status = ["Hadir", "Izin", "Sakit", "WFH"]
        if status not in allowed_status:
            return jsonify({"success": False, "message": f"Status tidak valid: {status}"}), 400

        # Timestamp saat ini
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Ambil IP address client
        client_ip = request.remote_addr or "unknown"

        # Simpan ke sheet "Absensi"
        append_row("Absensi", [timestamp, nama, status, catatan, client_ip])

        # Simpan ke sheet "Audit_Log"
        detail = f"Status: {status}"
        if catatan:
            detail += f" | Catatan: {catatan}"
        append_row("Audit_Log", [timestamp, "Absensi", nama, detail])

        # Kirim notifikasi Telegram
        telegram_message = (
            f"<b>Absensi Tercatat</b>\n"
            f"Nama: {nama}\n"
            f"Status: {status}\n"
            f"Waktu: {timestamp}"
        )
        if catatan:
            telegram_message += f"\nCatatan: {catatan}"

        telegram_sent = send_notification(telegram_message)

        if not telegram_sent:
            logger.warning("Notifikasi Telegram gagal dikirim, tapi data sudah tersimpan")

        return jsonify({
            "success": True,
            "message": f"Kehadiran {nama} berhasil dicatat",
            "telegram_sent": telegram_sent,
        })

    except Exception as e:
        logger.error(f"Error saat submit absensi: {e}")
        return jsonify({"success": False, "message": "Terjadi kesalahan server"}), 500


@absensi_bp.route("/api/log")
def api_log():
    """
    API endpoint untuk mengambil data audit log terbaru.
    Digunakan oleh JavaScript untuk refresh tabel.
    """
    try:
        all_records = get_all_records("Absensi")
        # Ambil 20 record terakhir, urutan terbaru di atas
        recent = list(reversed(all_records[-20:]))
        return jsonify({"log": recent})
    except Exception as e:
        logger.error(f"Error mengambil audit log: {e}")
        return jsonify({"log": []}), 500
