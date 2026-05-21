"""
Modul Face Authentication.
Semua logic face recognition untuk verifikasi wajah admin.
Menggunakan library face_recognition + OpenCV.
"""

import os
import logging
import base64

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Cache untuk menyimpan face encoding admin
# Format: {username: numpy_array_encoding}
_admin_face_encodings = {}

# Flag untuk mengecek apakah face_recognition tersedia
_face_recognition_available = False

try:
    import face_recognition
    _face_recognition_available = True
    logger.info("Library face_recognition berhasil dimuat")
except ImportError:
    logger.warning(
        "Library face_recognition tidak tersedia. "
        "Face verification akan menggunakan fallback OpenCV Haar Cascade."
    )


def load_admin_faces():
    """
    Memuat dan meng-encode semua foto referensi admin saat aplikasi start.
    Foto disimpan di folder ADMIN_FACES_DIR (dari .env).
    Nama file = username (contoh: rifki.jpg → username 'rifki').

    Hasil encoding di-cache di _admin_face_encodings agar tidak
    perlu re-encode setiap kali ada request verifikasi.
    """
    global _admin_face_encodings
    _admin_face_encodings = {}

    faces_dir = os.getenv("ADMIN_FACES_DIR", "static/assets/admin_faces")

    if not os.path.isdir(faces_dir):
        logger.warning(f"Folder foto admin tidak ditemukan: {faces_dir}")
        return

    # Ekstensi file foto yang didukung
    supported_ext = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    loaded_count = 0

    for filename in os.listdir(faces_dir):
        name, ext = os.path.splitext(filename)
        if ext.lower() not in supported_ext:
            continue

        filepath = os.path.join(faces_dir, filename)

        try:
            if _face_recognition_available:
                # Gunakan face_recognition untuk encoding yang akurat
                image = face_recognition.load_image_file(filepath)
                encodings = face_recognition.face_encodings(image)

                if len(encodings) == 0:
                    logger.warning(
                        f"Tidak ada wajah terdeteksi di foto: {filename}"
                    )
                    continue

                if len(encodings) > 1:
                    logger.warning(
                        f"Lebih dari 1 wajah terdeteksi di {filename}, "
                        "menggunakan wajah pertama"
                    )

                # Cache encoding wajah dengan key = username (tanpa ekstensi)
                _admin_face_encodings[name.lower()] = encodings[0]
                loaded_count += 1
                logger.info(f"Face encoding berhasil dimuat untuk: {name}")

            else:
                # Fallback: simpan path saja, verifikasi pakai Haar Cascade
                _admin_face_encodings[name.lower()] = filepath
                loaded_count += 1
                logger.info(
                    f"Path foto disimpan (fallback mode) untuk: {name}"
                )

        except Exception as e:
            logger.error(f"Gagal memuat foto admin '{filename}': {e}")

    logger.info(
        f"Total {loaded_count} foto admin berhasil dimuat dari '{faces_dir}'"
    )


def verify_face(username, image_base64):
    """
    Verifikasi wajah dari gambar base64 terhadap foto referensi admin.

    Args:
        username: Username admin yang akan diverifikasi.
        image_base64: String base64 dari gambar wajah (dari webcam/upload).

    Returns:
        dict: {
            'match': bool,
            'message': str,
            'confidence': float (0-1, semakin rendah semakin cocok)
        }
    """
    username_lower = username.lower()

    # Cek apakah ada foto referensi untuk username ini
    if username_lower not in _admin_face_encodings:
        return {
            "match": False,
            "message": f"Foto referensi untuk '{username}' tidak ditemukan. "
                       f"Pastikan file {username}.jpg ada di folder admin_faces.",
            "confidence": 1.0,
        }

    try:
        # Decode base64 ke bytes gambar
        image_bytes = _decode_base64_image(image_base64)
        if image_bytes is None:
            return {
                "match": False,
                "message": "Format gambar tidak valid atau gagal di-decode.",
                "confidence": 1.0,
            }

        # Convert bytes ke numpy array (OpenCV format)
        np_array = np.frombuffer(image_bytes, np.uint8)
        cv_image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if cv_image is None:
            return {
                "match": False,
                "message": "Gagal membaca gambar. Pastikan format gambar valid.",
                "confidence": 1.0,
            }

        # Jalankan verifikasi berdasarkan library yang tersedia
        if _face_recognition_available:
            return _verify_with_face_recognition(username_lower, cv_image)
        else:
            return _verify_with_opencv_fallback(username_lower, cv_image)

    except Exception as e:
        logger.error(f"Error saat verifikasi wajah untuk '{username}': {e}")
        return {
            "match": False,
            "message": "Terjadi kesalahan saat memproses verifikasi wajah.",
            "confidence": 1.0,
        }


def _decode_base64_image(image_base64):
    """
    Decode string base64 menjadi bytes gambar.
    Mendukung format data URL (data:image/...;base64,...) dan raw base64.

    Returns:
        bytes atau None jika gagal decode.
    """
    try:
        # Hapus header data URL jika ada (data:image/jpeg;base64,...)
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        # Hapus whitespace
        image_base64 = image_base64.strip()

        return base64.b64decode(image_base64)

    except Exception as e:
        logger.error(f"Gagal decode base64 image: {e}")
        return None


def _verify_with_face_recognition(username, cv_image):
    """
    Verifikasi wajah menggunakan library face_recognition (akurat).
    Membandingkan encoding wajah dari gambar input dengan encoding
    referensi yang sudah di-cache.

    Args:
        username: Username admin (lowercase).
        cv_image: Gambar dalam format OpenCV (BGR numpy array).

    Returns:
        dict dengan keys: match, message, confidence.
    """
    tolerance = float(os.getenv("FACE_TOLERANCE", "0.5"))
    reference_encoding = _admin_face_encodings[username]

    # Convert BGR (OpenCV) ke RGB (face_recognition)
    rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

    # Detect dan encode wajah dari gambar input
    face_locations = face_recognition.face_locations(rgb_image)

    if len(face_locations) == 0:
        return {
            "match": False,
            "message": "Tidak ada wajah terdeteksi dalam gambar. "
                       "Pastikan wajah terlihat jelas dan pencahayaan cukup.",
            "confidence": 1.0,
        }

    # Encode wajah yang terdeteksi
    input_encodings = face_recognition.face_encodings(rgb_image, face_locations)

    if len(input_encodings) == 0:
        return {
            "match": False,
            "message": "Gagal menghasilkan encoding wajah dari gambar.",
            "confidence": 1.0,
        }

    # Bandingkan dengan foto referensi (gunakan wajah pertama yang terdeteksi)
    input_encoding = input_encodings[0]
    face_distance = face_recognition.face_distance(
        [reference_encoding], input_encoding
    )[0]

    # face_distance: semakin kecil semakin mirip (0 = identik)
    is_match = face_distance <= tolerance

    if is_match:
        logger.info(
            f"Wajah cocok untuk '{username}' "
            f"(distance: {face_distance:.4f}, tolerance: {tolerance})"
        )
        return {
            "match": True,
            "message": "Verifikasi wajah berhasil!",
            "confidence": round(float(face_distance), 4),
        }
    else:
        logger.warning(
            f"Wajah TIDAK cocok untuk '{username}' "
            f"(distance: {face_distance:.4f}, tolerance: {tolerance})"
        )
        return {
            "match": False,
            "message": "Wajah tidak dikenali. Pastikan wajah Anda terlihat "
                       "jelas dan cocok dengan foto referensi.",
            "confidence": round(float(face_distance), 4),
        }


def _verify_with_opencv_fallback(username, cv_image):
    """
    Fallback verifikasi wajah menggunakan OpenCV Haar Cascade.
    Metode ini hanya mendeteksi apakah ada wajah, lalu membandingkan
    histogram warna dengan foto referensi. Kurang akurat dibanding
    face_recognition, tapi tidak perlu dlib/cmake.

    Args:
        username: Username admin (lowercase).
        cv_image: Gambar dalam format OpenCV (BGR numpy array).

    Returns:
        dict dengan keys: match, message, confidence.
    """
    reference_path = _admin_face_encodings[username]

    # Load Haar Cascade untuk deteksi wajah
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Convert ke grayscale untuk deteksi
    gray_input = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    faces_input = face_cascade.detectMultiScale(
        gray_input, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces_input) == 0:
        return {
            "match": False,
            "message": "Tidak ada wajah terdeteksi dalam gambar. "
                       "Pastikan wajah terlihat jelas dan pencahayaan cukup.",
            "confidence": 1.0,
        }

    # Load dan proses foto referensi
    ref_image = cv2.imread(reference_path)
    if ref_image is None:
        return {
            "match": False,
            "message": "Gagal membaca foto referensi admin.",
            "confidence": 1.0,
        }

    gray_ref = cv2.cvtColor(ref_image, cv2.COLOR_BGR2GRAY)
    faces_ref = face_cascade.detectMultiScale(
        gray_ref, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )

    if len(faces_ref) == 0:
        return {
            "match": False,
            "message": "Tidak ada wajah terdeteksi di foto referensi admin.",
            "confidence": 1.0,
        }

    # Crop wajah dari kedua gambar
    (x, y, w, h) = faces_input[0]
    face_input = cv_image[y:y + h, x:x + w]

    (rx, ry, rw, rh) = faces_ref[0]
    face_ref = ref_image[ry:ry + rh, rx:rx + rw]

    # Resize ke ukuran yang sama untuk perbandingan
    target_size = (128, 128)
    face_input_resized = cv2.resize(face_input, target_size)
    face_ref_resized = cv2.resize(face_ref, target_size)

    # Bandingkan menggunakan histogram correlation
    hist_input = cv2.calcHist(
        [face_input_resized], [0, 1, 2], None,
        [32, 32, 32], [0, 256, 0, 256, 0, 256]
    )
    hist_ref = cv2.calcHist(
        [face_ref_resized], [0, 1, 2], None,
        [32, 32, 32], [0, 256, 0, 256, 0, 256]
    )

    cv2.normalize(hist_input, hist_input)
    cv2.normalize(hist_ref, hist_ref)

    # Correlation: 1.0 = identik, 0.0 = tidak mirip
    similarity = cv2.compareHist(hist_input, hist_ref, cv2.HISTCMP_CORREL)

    tolerance = float(os.getenv("FACE_TOLERANCE", "0.5"))
    # Untuk fallback, kita gunakan threshold similarity
    # Konversi agar konsisten: distance = 1 - similarity
    distance = 1.0 - max(0.0, similarity)
    is_match = distance <= tolerance

    if is_match:
        logger.info(
            f"Wajah cocok (fallback) untuk '{username}' "
            f"(similarity: {similarity:.4f}, distance: {distance:.4f})"
        )
        return {
            "match": True,
            "message": "Verifikasi wajah berhasil! (mode fallback)",
            "confidence": round(float(distance), 4),
        }
    else:
        logger.warning(
            f"Wajah TIDAK cocok (fallback) untuk '{username}' "
            f"(similarity: {similarity:.4f}, distance: {distance:.4f})"
        )
        return {
            "match": False,
            "message": "Wajah tidak dikenali. Pastikan wajah Anda terlihat "
                       "jelas dan cocok dengan foto referensi.",
            "confidence": round(float(distance), 4),
        }


def get_loaded_admins():
    """
    Mengembalikan daftar username admin yang foto-nya sudah ter-load.
    Berguna untuk debugging / status check.

    Returns:
        list: Daftar username admin yang face encoding-nya sudah di-cache.
    """
    return list(_admin_face_encodings.keys())


def is_face_recognition_available():
    """
    Cek apakah library face_recognition tersedia.

    Returns:
        bool: True jika face_recognition bisa digunakan.
    """
    return _face_recognition_available
