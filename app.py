"""
Productivity Suite — PT Telkom Indonesia (Enterprise Division)
Aplikasi web Flask multi-halaman untuk manajemen kehadiran,
dashboard analytics, dan generator artikel AI.
"""

import logging
import os

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from flask_caching import Cache

# Muat environment variables dari .env
load_dotenv()

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Shared Flask-Caching instance (filesystem backend, 1-hour TTL)
# Initialised inside create_app() so it shares the app context.
cache = Cache()


def create_app():
    """
    Application factory — membuat dan mengkonfigurasi Flask app.
    """
    app = Flask(__name__)

    # Konfigurasi secret key untuk session
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())

    # Konfigurasi session agar bisa menyimpan data besar (word cloud base64)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

    # === Flask-Caching: filesystem backend for word clouds ===
    wc_cache_dir = os.path.join(app.root_path, "static", "wordcloud_cache")
    os.makedirs(wc_cache_dir, exist_ok=True)
    app.config["CACHE_TYPE"] = "FileSystemCache"
    app.config["CACHE_DIR"] = wc_cache_dir
    app.config["CACHE_DEFAULT_TIMEOUT"] = 3600  # 1 hour
    cache.init_app(app)

    # === Register Blueprints ===
    from blueprints.absensi import absensi_bp
    from blueprints.artikel import artikel_bp
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(absensi_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(artikel_bp)

    # === Login Guard Global ===
    # Halaman yang tidak perlu login
    PUBLIC_ENDPOINTS = {
        "auth.login_page",
        "auth.login_submit",
        "auth.verify_face_endpoint",
        "static",
    }

    @app.before_request
    def require_login():
        """
        Middleware: redirect ke login jika belum authenticated.
        Skip untuk endpoint publik (login, static files).
        """
        if request.endpoint in PUBLIC_ENDPOINTS:
            return None
        if request.endpoint and request.endpoint.startswith("static"):
            return None
        if not session.get("logged_in"):
            return redirect(url_for("auth.login_page"))
        return None

    # === Route: Root redirect ===
    @app.route("/")
    def index():
        """Redirect root ke halaman Absensi (jika sudah login)."""
        if session.get("logged_in"):
            return redirect(url_for("absensi.index"))
        return redirect(url_for("auth.login_page"))

    # === Error Handlers ===
    @app.errorhandler(404)
    def not_found(e):
        """Handler untuk halaman tidak ditemukan."""
        return render_template("base.html", error="Halaman tidak ditemukan"), 404

    @app.errorhandler(500)
    def server_error(e):
        """Handler untuk error server."""
        logger.error(f"Server error: {e}")
        return render_template("base.html", error="Terjadi kesalahan pada server"), 500

    # === Muat face encoding admin saat app start ===
    with app.app_context():
        # Mulai background write worker untuk Google Sheets
        try:
            from utils.sheets import start_write_worker

            start_write_worker()
        except Exception as e:
            logger.warning(f"Gagal memulai Sheets write worker: {e}")

        try:
            from utils.face_auth import load_admin_faces

            load_admin_faces()
            logger.info("Face encoding admin berhasil dimuat")
        except Exception as e:
            logger.warning(f"Gagal memuat face encoding admin: {e}")

        # Pastikan tab Login_Log ada di Google Sheets
        try:
            from utils.sheets import ensure_login_log_sheet

            ensure_login_log_sheet()
        except Exception as e:
            logger.warning(f"Gagal memastikan tab Login_Log: {e}")

    logger.info("Productivity Suite berhasil diinisialisasi")
    return app


# Entry point
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
