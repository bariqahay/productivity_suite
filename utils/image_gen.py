"""
Modul untuk generate word cloud dari teks artikel.
Menggunakan library WordCloud untuk visualisasi frekuensi kata,
dengan color mapping tema merah Telkom (Reds).
"""

import io
import re
import logging
import base64

from wordcloud import WordCloud

logger = logging.getLogger(__name__)


def generate_wordcloud(text: str) -> str | None:
    """
    Generate word cloud dari teks artikel.
    Proses:
      1. Bersihkan teks (hapus tanda baca, lowercase)
      2. Generate word cloud dengan colormap Reds
      3. Simpan sebagai PNG ke buffer
      4. Encode ke base64 string

    Args:
        text: Teks artikel yang akan divisualisasikan.

    Returns:
        str: Base64 encoded PNG string, atau None jika teks kosong.
    """
    # Validasi: kembalikan None jika teks kosong
    if not text or not text.strip():
        logger.warning("Teks artikel kosong, word cloud tidak di-generate")
        return None

    try:
        # Bersihkan teks: hapus tanda baca, ubah ke lowercase
        clean_text = re.sub(r'[^\w\s]', '', text.lower())

        # Hapus angka yang berdiri sendiri
        clean_text = re.sub(r'\b\d+\b', '', clean_text)

        # Hapus whitespace berlebih
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        if not clean_text:
            logger.warning("Teks setelah dibersihkan kosong")
            return None

        # Generate word cloud dengan tema merah Telkom
        wc = WordCloud(
            width=800,
            height=400,
            background_color='white',
            colormap='Reds',            # Tema warna merah Telkom
            max_words=80,
            collocations=False,         # Hindari pengulangan pasangan kata
            font_path=None,             # Gunakan font default sistem
            min_font_size=10,
            max_font_size=120,
            random_state=42,            # Konsistensi layout
        ).generate(clean_text)

        # Convert gambar word cloud ke bytes PNG
        buf = io.BytesIO()
        wc.to_image().save(buf, format='PNG')
        buf.seek(0)

        # Encode ke base64 untuk transfer ke frontend
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        logger.info(f"Word cloud berhasil di-generate ({len(clean_text)} karakter teks)")
        return img_base64

    except Exception as e:
        logger.error(f"Gagal generate word cloud: {e}")
        return None
