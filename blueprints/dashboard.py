"""
Blueprint: Dashboard
Menyediakan analytics kehadiran dengan Chart.js (bar, donut, line),
rekap per karyawan, K-Means clustering, dan export Excel.
"""

import io
import os
import logging
import time
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from utils.sheets import get_all_records

logger = logging.getLogger(__name__)

# Rate limiting sederhana untuk /api/present-count
# Format: {ip: timestamp_terakhir_request}
_present_count_rate_limit = {}

# Definisi blueprint
dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
)


@dashboard_bp.route("/")
def index():
    """Halaman utama Dashboard."""
    # Ambil lokasi kantor dari .env untuk info card
    office_location = os.getenv("OFFICE_LOCATION", "Tidak diatur")
    return render_template("dashboard.html", office_location=office_location)


@dashboard_bp.route("/api/data")
def api_data():
    """
    API endpoint utama dashboard.
    Mengembalikan semua data yang diperlukan oleh chart dan tabel.
    Query param: period = week | month | all
    """
    try:
        period = request.args.get("period", "all")

        # Ambil semua record kehadiran
        all_records = get_all_records("Absensi")

        if not all_records:
            return jsonify({
                "daily": {},
                "status_distribution": {},
                "weekly_trend": {},
                "rekap": [],
            })

        # Konversi ke DataFrame
        df = pd.DataFrame(all_records)

        # Parse timestamp menjadi datetime
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed", errors="coerce")

        # Hapus baris dengan timestamp invalid
        df = df.dropna(subset=["Timestamp"])

        if df.empty:
            return jsonify({
                "daily": {},
                "status_distribution": {},
                "weekly_trend": {},
                "rekap": [],
            })

        # Filter berdasarkan periode
        now = datetime.now()
        if period == "week":
            # Minggu ini (Senin - Minggu)
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            df = df[df["Timestamp"] >= start_of_week]
        elif period == "month":
            # Bulan ini
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            df = df[df["Timestamp"] >= start_of_month]
        # 'all' = tidak ada filter

        if df.empty:
            return jsonify({
                "daily": {},
                "status_distribution": {},
                "weekly_trend": {},
                "rekap": [],
            })

        # === 1. Kehadiran Harian (bar chart) ===
        df["Tanggal"] = df["Timestamp"].dt.strftime("%d %b")
        daily_counts = df.groupby("Tanggal").size()
        # Urutkan berdasarkan tanggal asli
        df_sorted = df.sort_values("Timestamp")
        ordered_dates = df_sorted["Tanggal"].unique()
        daily = {date: int(daily_counts.get(date, 0)) for date in ordered_dates}

        # === 2. Distribusi Status (donut chart) ===
        status_dist = df["Status"].value_counts().to_dict()
        status_distribution = {k: int(v) for k, v in status_dist.items()}

        # === 3. Tren Mingguan (line chart) ===
        df["Minggu"] = df["Timestamp"].dt.isocalendar().week.astype(str)
        df["Tahun"] = df["Timestamp"].dt.year.astype(str)
        df["MingguLabel"] = "W" + df["Minggu"]
        weekly_counts = df.groupby(["Tahun", "MingguLabel"]).size()
        weekly_trend = {}
        for (tahun, minggu), count in weekly_counts.items():
            label = f"{minggu}"
            weekly_trend[label] = int(count)

        # === 4. Rekap Per Karyawan + K-Means Clustering ===
        rekap = _build_rekap_with_clustering(df)

        return jsonify({
            "daily": daily,
            "status_distribution": status_distribution,
            "weekly_trend": weekly_trend,
            "rekap": rekap,
        })

    except Exception as e:
        logger.error(f"[ERROR] dashboard - Gagal memuat data dashboard: {e}")
        return jsonify({"error": "Gagal memuat data dashboard"}), 500


def _build_rekap_with_clustering(df):
    """
    Membuat rekap per karyawan dan menjalankan K-Means clustering.
    Kluster: Konsisten, Sering Izin, Tidak Konsisten.
    """
    try:
        # Agregasi per karyawan
        rekap_data = []
        grouped = df.groupby("Nama")

        for nama, group in grouped:
            total = len(group)
            hadir = len(group[group["Status"].isin(["Hadir", "WFH"])])
            izin = len(group[group["Status"] == "Izin"])
            sakit = len(group[group["Status"] == "Sakit"])

            rekap_data.append({
                "nama": nama,
                "total_hadir": hadir,
                "izin": izin,
                "sakit": sakit,
                "total": total,
            })

        if not rekap_data:
            return []

        rekap_df = pd.DataFrame(rekap_data)

        # K-Means clustering (hanya jika ada cukup data)
        if len(rekap_df) >= 3:
            features = rekap_df[["total_hadir", "izin", "sakit"]].values

            # Normalisasi fitur
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            # Jalankan K-Means dengan 3 kluster
            n_clusters = min(3, len(rekap_df))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            rekap_df["cluster"] = kmeans.fit_predict(features_scaled)

            # Mapping kluster berdasarkan rasio kehadiran
            cluster_labels = _map_cluster_labels(rekap_df, kmeans)
            rekap_df["kluster"] = rekap_df["cluster"].map(cluster_labels)
        elif len(rekap_df) > 0:
            # Jika data kurang dari 3, assign berdasarkan rasio sederhana
            rekap_df["kluster"] = rekap_df.apply(
                lambda row: _simple_label(row), axis=1
            )

        # Konversi ke list of dict
        result = []
        for _, row in rekap_df.iterrows():
            result.append({
                "nama": row["nama"],
                "total_hadir": int(row["total_hadir"]),
                "izin": int(row["izin"]),
                "sakit": int(row["sakit"]),
                "kluster": row.get("kluster", "-"),
            })

        return result

    except Exception as e:
        logger.error(f"Error saat clustering: {e}")
        # Fallback: return rekap tanpa kluster
        return [{
            "nama": r["nama"],
            "total_hadir": r["total_hadir"],
            "izin": r["izin"],
            "sakit": r["sakit"],
            "kluster": "-",
        } for r in rekap_data]


def _map_cluster_labels(rekap_df, kmeans):
    """
    Mapping label kluster berdasarkan centroid K-Means.
    Cluster dengan rasio hadir tertinggi = Konsisten,
    Cluster dengan izin tertinggi = Sering Izin,
    Sisanya = Tidak Konsisten.
    """
    centers = kmeans.cluster_centers_
    labels = {}

    # Hitung rasio kehadiran per cluster
    cluster_stats = []
    for i in range(len(centers)):
        cluster_data = rekap_df[rekap_df["cluster"] == i]
        if not cluster_data.empty:
            avg_hadir_ratio = cluster_data["total_hadir"].sum() / max(cluster_data["total"].sum(), 1)
            avg_izin_ratio = cluster_data["izin"].sum() / max(cluster_data["total"].sum(), 1)
        else:
            avg_hadir_ratio = 0
            avg_izin_ratio = 0
        cluster_stats.append({
            "cluster": i,
            "hadir_ratio": avg_hadir_ratio,
            "izin_ratio": avg_izin_ratio,
        })

    # Urutkan berdasarkan rasio kehadiran (tertinggi = Konsisten)
    cluster_stats.sort(key=lambda x: x["hadir_ratio"], reverse=True)

    label_options = ["Konsisten", "Sering Izin", "Tidak Konsisten"]

    for i, stat in enumerate(cluster_stats):
        if i < len(label_options):
            labels[stat["cluster"]] = label_options[i]
        else:
            labels[stat["cluster"]] = "Tidak Konsisten"

    return labels


def _simple_label(row):
    """Label sederhana jika data kurang untuk clustering."""
    total = row["total"] if row["total"] > 0 else 1
    hadir_ratio = row["total_hadir"] / total

    if hadir_ratio >= 0.8:
        return "Konsisten"
    elif row["izin"] > row["sakit"]:
        return "Sering Izin"
    else:
        return "Tidak Konsisten"


@dashboard_bp.route("/api/present-count")
def api_present_count():
    """
    API endpoint untuk menghitung persentase kehadiran hari ini.
    Rate limit: maksimum 1 request per 5 detik per IP.
    Mengembalikan: { percent, hadir_count, total_karyawan }
    """
    try:
        # Rate limiting: 1 request per 5 detik per IP
        client_ip = request.remote_addr or "unknown"
        now = time.time()
        last_request = _present_count_rate_limit.get(client_ip, 0)
        if now - last_request < 5:
            return jsonify({
                "error": "Terlalu banyak request. Coba lagi beberapa detik."
            }), 429
        _present_count_rate_limit[client_ip] = now

        # Bersihkan entry lama (lebih dari 60 detik) agar tidak bocor memori
        expired_ips = [ip for ip, ts in _present_count_rate_limit.items() if now - ts > 60]
        for ip in expired_ips:
            del _present_count_rate_limit[ip]

        # Ambil total karyawan dari tab "Karyawan"
        karyawan_records = get_all_records("Karyawan")
        total_karyawan = len(karyawan_records)

        if total_karyawan == 0:
            return jsonify({
                "percent": 0,
                "hadir_count": 0,
                "total_karyawan": 0,
            })

        # Ambil semua record absensi
        absensi_records = get_all_records("Absensi")

        # Filter: Status="Hadir" DAN tanggal=hari ini
        today_str = datetime.now().strftime("%Y-%m-%d")
        hadir_count = 0
        nama_sudah_hadir = set()  # Hindari duplikasi per karyawan

        for record in absensi_records:
            timestamp = record.get("Timestamp", "")
            status = record.get("Status", "")
            nama = record.get("Nama", "")

            # Cek apakah timestamp dimulai dengan tanggal hari ini
            if (timestamp.startswith(today_str)
                    and status == "Hadir"
                    and nama not in nama_sudah_hadir):
                hadir_count += 1
                nama_sudah_hadir.add(nama)

        # Hitung persentase
        percent = round((hadir_count / total_karyawan) * 100)

        return jsonify({
            "percent": percent,
            "hadir_count": hadir_count,
            "total_karyawan": total_karyawan,
        })

    except Exception as e:
        logger.error(f"[ERROR] dashboard - Gagal menghitung kehadiran hari ini: {e}")
        return jsonify({"error": "Gagal menghitung data kehadiran"}), 500


@dashboard_bp.route("/api/export")
def api_export():
    """
    Export data rekap ke file Excel (.xlsx).
    """
    try:
        all_records = get_all_records("Absensi")
        if not all_records:
            return jsonify({"error": "Tidak ada data untuk di-export"}), 404

        df = pd.DataFrame(all_records)

        # Buat file Excel di memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Rekap Kehadiran", index=False)
        output.seek(0)

        filename = f"rekap_kehadiran_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        logger.error(f"Error export Excel: {e}")
        return jsonify({"error": "Gagal export data"}), 500
