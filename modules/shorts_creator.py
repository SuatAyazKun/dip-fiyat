"""
YouTube Shorts icin pro 9:16 animasyonlu video olusturur.
60 FPS, 30 saniye, sinematik sahne gecisleri.
Cikis: output/shorts/ klasorunde MP4 dosyasi
"""
import os
import sys
import subprocess
import logging
import requests
import tempfile
import shutil
import math
import random
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

W, H       = 1080, 1920
FPS        = 60
DURATION   = 30
FFMPEG     = config.FFMPEG_PATH
OUTPUT_DIR = os.path.join(config.BASE_DIR, "output", "shorts")


# ─────────────────────────────────────────────────────────────
# Yardimci fonksiyonlar
# ─────────────────────────────────────────────────────────────

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _tw(draw, text: str, font) -> float:
    try:
        return draw.textlength(text, font=font)
    except Exception:
        b = font.getbbox(text)
        return b[2] - b[0]


def _th(font, text="A") -> int:
    try:
        b = font.getbbox(text)
        return b[3] - b[1]
    except Exception:
        return font.size


def _center_x(draw, text, font, y, color, shadow=True):
    w = _tw(draw, text, font)
    x = (W - w) / 2
    if shadow:
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 120))
    draw.text((x, y), text, font=font, fill=color)


def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if _tw(draw, test, font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _ease_out_cubic(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _ease_in_out_cubic(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 4 * x**3 if x < 0.5 else 1 - (-2 * x + 2)**3 / 2


def _elastic_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    if x == 0 or x == 1:
        return x
    return 2**(-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1


def _bounce_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    n1, d1 = 7.5625, 2.75
    if x < 1 / d1:
        return n1 * x * x
    elif x < 2 / d1:
        x -= 1.5 / d1
        return n1 * x * x + 0.75
    elif x < 2.5 / d1:
        x -= 2.25 / d1
        return n1 * x * x + 0.9375
    else:
        x -= 2.625 / d1
        return n1 * x * x + 0.984375


def _download_image(url: str):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        logger.error("Gorsel indirilemedi: %s", e)
        return None


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return tuple(int(_lerp(a, b, t)) for a, b in zip(c1, c2))


# ─────────────────────────────────────────────────────────────
# Arka plan katmanı — gradient + particle efekti
# ─────────────────────────────────────────────────────────────

# Statik partiküller (frame'ler arasında sabit konum, sadece alpha animasyonlu)
_PARTICLES = [(random.randint(0, W), random.randint(0, H), random.uniform(0, math.pi * 2)) for _ in range(40)]


def _draw_background(canvas, draw, t_global):
    """Dinamik gradient arka plan + parlayan partiküller."""
    # Gradient: üstten alta (koyu lacivert → siyah mor)
    top_col = (8, 8, 22)
    bot_col = (22, 8, 35)
    for y in range(H):
        frac = y / H
        c = _lerp_color(top_col, bot_col, frac)
        draw.line([(0, y), (W, y)], fill=c)

    # Işıklı diyagonal çizgiler (hız hissi)
    line_alpha = 18
    for i in range(-H, W + H, 110):
        x0, y0 = i, 0
        x1, y1 = i + H, H
        draw.line([(x0, y0), (x1, y1)], fill=(30, 30, 60), width=1)

    # Partiküller — yavaşça titreşiyor
    for px, py, phase in _PARTICLES:
        brightness = 0.3 + 0.7 * abs(math.sin(t_global * 2 + phase))
        r = int(80 * brightness)
        g = int(120 * brightness)
        b = int(220 * brightness)
        size = int(2 + 3 * brightness)
        draw.ellipse([px - size, py - size, px + size, py + size], fill=(r, g, b))


# ─────────────────────────────────────────────────────────────
# Sahne kartlari
# ─────────────────────────────────────────────────────────────

def _draw_header(draw, t, bold, light):
    """Üst bant — logo ve slogan."""
    HDR_H = 180
    # Arka plan bant gradyanı (turuncu → kırmızı)
    for x in range(W):
        frac = x / W
        c = _lerp_color((255, 90, 0), (220, 20, 60), frac)
        draw.line([(x, 0), (x, HDR_H)], fill=c)

    # Alt gölge
    for dy in range(20):
        alpha = int(180 * (1 - dy / 20))
        draw.line([(0, HDR_H + dy), (W, HDR_H + dy)], fill=(0, 0, 0))

    f_logo = _font(bold, 96)
    f_sub  = _font(light, 34)
    _center_x(draw, "DIP FIYAT", f_logo, y=28, color=(255, 255, 255), shadow=True)
    _center_x(draw, "Amazon'un En Iyi Firsatlari", f_sub, y=124, color=(255, 220, 200), shadow=False)


def _draw_product_card(canvas, draw, deal, product_img, t_enter, t_global, bold, light):
    """
    Ürün kartı — yukarıdan düşer + hafif rotate + bounce.
    t_enter: 0→1 (kart giriş animasyonu)
    """
    CARD_LEFT   = 30
    CARD_RIGHT  = W - 30
    CARD_TOP    = 200
    CARD_BOTTOM = 1000
    CARD_W      = CARD_RIGHT - CARD_LEFT
    CARD_H      = CARD_BOTTOM - CARD_TOP
    RADIUS      = 36

    p = _bounce_out(t_enter)

    # Kart yukarıdan iner
    off_y = int((1 - p) * -H * 0.6)
    # Hafif eğim (dönüş hissi) — rotate yerine perspektif kaydırma
    skew = int((1 - p) * 40)

    ct = CARD_TOP + off_y
    cb = CARD_BOTTOM + off_y

    # Kart gölgesi
    shadow_offset = 12
    draw.rounded_rectangle(
        [CARD_LEFT + shadow_offset, ct + shadow_offset,
         CARD_RIGHT + shadow_offset, cb + shadow_offset],
        radius=RADIUS, fill=(0, 0, 0)
    )

    # Beyaz kart
    draw.rounded_rectangle(
        [CARD_LEFT, ct, CARD_RIGHT, cb],
        radius=RADIUS, fill=(252, 252, 255)
    )

    # Ürün görseli
    if product_img and t_enter > 0.1:
        img_p = min(1.0, _ease_out_cubic((t_enter - 0.1) / 0.9))
        pi = product_img.copy()
        img_max_w = CARD_W - 60
        img_max_h = CARD_H - 60
        pi.thumbnail((img_max_w, img_max_h), Image.LANCZOS)

        # Fade in
        if img_p < 1.0:
            r_ch, g_ch, b_ch, a_ch = pi.split()
            a_ch = a_ch.point(lambda v: int(v * img_p))
            pi = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

        px = CARD_LEFT + (CARD_W - pi.width) // 2
        py = ct + (CARD_H - pi.height) // 2
        canvas.paste(pi, (px, py), pi)

    # İndirim rozeti — sağ üst köşeden fırlar
    disc = deal.get("discount_pct", 0)
    if disc >= 1 and t_enter > 0.4:
        badge_p = _elastic_out((t_enter - 0.4) / 0.6)
        pulse   = 1.0 + 0.05 * math.sin(t_global * 8)

        f_badge_big = _font(bold, 52)
        f_badge_sub = _font(light, 28)
        big_text = f"%{int(disc)}"
        sub_text = "INDIRIM"

        bw = int(160 * pulse)
        bh = int(160 * pulse)
        bx = int(CARD_RIGHT - bw - 10 + (1 - badge_p) * 300)
        by = ct + 15

        # Dairesel rozet
        draw.ellipse([bx, by, bx + bw, by + bh], fill=(220, 20, 60))
        # Parlama üst yarısı
        draw.ellipse([bx, by, bx + bw, by + bh // 2 + 10], fill=(255, 60, 80))

        big_w = _tw(draw, big_text, f_badge_big)
        sub_w = _tw(draw, sub_text, f_badge_sub)
        cx = bx + bw // 2
        draw.text((cx - big_w / 2, by + 28), big_text, font=f_badge_big, fill=(255, 255, 255))
        draw.text((cx - sub_w / 2, by + 96), sub_text, font=f_badge_sub, fill=(255, 220, 220))

    return CARD_BOTTOM + off_y  # alt kenar y koordinatı


def _draw_info_section(draw, deal, card_bottom, t_info, bold, light):
    """
    Başlık + fiyat bilgisi — kartın hemen altında.
    t_info: 0→1 (bilgi girişi animasyonu)
    """
    f_title  = _font(bold, 52)
    f_price  = _font(bold, 120)
    f_old    = _font(light, 44)
    f_saving = _font(bold, 38)

    y = card_bottom + 30

    # Başlık satırları — soldan slayt
    title = deal.get("title", "Urun Adi")
    lines = _wrap(draw, title, f_title, W - 80)[:2]
    for i, line in enumerate(lines):
        line_t = max(0.0, (t_info - i * 0.08) / 0.25)
        p = _ease_out_cubic(line_t)
        off_x = int((1 - p) * -200)
        draw.text((40 + off_x, y), line, font=f_title, fill=(240, 240, 255))
        y += _th(f_title) + 8

    y += 16

    cur  = deal.get("current_price", 0)
    orig = deal.get("original_price", 0)

    # Eski fiyat (üstü çizili)
    if orig and orig > cur and t_info > 0.2:
        p_old = _ease_out_cubic((t_info - 0.2) / 0.3)
        off_x = int((1 - p_old) * 200)
        old_str = f"Normal Fiyat: {orig:,.0f} TL".replace(",", ".")
        ow = _tw(draw, old_str, f_old)
        draw.text((40 + off_x, y), old_str, font=f_old, fill=(180, 60, 60))
        draw.line(
            [(40 + off_x, y + _th(f_old) // 2),
             (40 + off_x + int(ow * p_old), y + _th(f_old) // 2)],
            fill=(200, 40, 40), width=3
        )
        y += _th(f_old) + 10

    # Yeni fiyat — zoom ile belirir
    if t_info > 0.35:
        p_price = _ease_out_cubic((t_info - 0.35) / 0.35)
        zoom = 1.5 - 0.5 * p_price
        price_str = f"{cur:,.0f} TL".replace(",", ".")
        pw = _tw(draw, price_str, f_price)
        px_pos = (W - pw) / 2

        if zoom != 1.0 and p_price < 1.0:
            tmp = Image.new("RGBA", (W, 180), (0, 0, 0, 0))
            td  = ImageDraw.Draw(tmp)
            td.text((px_pos, 20), price_str, font=f_price, fill=(30, 220, 100))
            new_w = int(W * zoom)
            new_h = int(180 * zoom)
            tmp = tmp.resize((new_w, new_h), Image.LANCZOS)
            ox = (W - new_w) // 2
            oy = y - int((new_h - 180) / 2)
            draw.rectangle([0, oy - 10, W, oy + new_h + 10], fill=None)
            tmp_rgb = Image.new("RGB", (W, H), (0, 0, 0))
            tmp_rgb.paste(tmp, (ox, oy), tmp)
        else:
            draw.text((px_pos, y + 10), price_str, font=f_price, fill=(30, 220, 100))

        # Tasarruf etiketi
        if orig and orig > cur and t_info > 0.65:
            saving = orig - cur
            p_save = _ease_out_cubic((t_info - 0.65) / 0.35)
            save_str = f"  {saving:,.0f} TL Tasarruf!  ".replace(",", ".")
            sw = _tw(draw, save_str, f_saving)
            sx = (W - sw) / 2
            sy = y + _th(f_price) + 20
            draw.rounded_rectangle(
                [sx - 10, sy - 6, sx + sw + 10, sy + _th(f_saving) + 14],
                radius=12, fill=(30, 180, 80)
            )
            draw.text((sx, sy), save_str, font=f_saving, fill=(255, 255, 255))


def _draw_cta_button(draw, t_cta, bold):
    """Alt CTA butonu — aşağıdan fırlar + nabız atar."""
    if t_cta <= 0:
        return

    p     = _bounce_out(min(1.0, t_cta / 0.4))
    pulse = 1.0 + 0.04 * math.sin(t_cta * 10)

    f_cta = _font(bold, 58)
    f_sub = _font(bold, 32)

    BTN_Y  = int(H - 260 + (1 - p) * 300)
    BTN_H  = 120
    MARGIN = 50

    # Gölge
    draw.rounded_rectangle(
        [MARGIN + 8, BTN_Y + 8, W - MARGIN + 8, BTN_Y + BTN_H + 8],
        radius=28, fill=(0, 0, 0)
    )

    # Gradient buton (turuncu → kırmızı)
    for x in range(MARGIN, W - MARGIN):
        frac = (x - MARGIN) / (W - 2 * MARGIN)
        c = _lerp_color((255, 100, 0), (220, 20, 60), frac)
        draw.line([(x, BTN_Y), (x, BTN_Y + BTN_H)], fill=c)

    # Üst parlama
    draw.rounded_rectangle(
        [MARGIN, BTN_Y, W - MARGIN, BTN_Y + BTN_H // 2],
        radius=28, fill=(255, 140, 40)
    )

    _center_x(draw, "Firsati Kacirma! ➜", f_cta, y=BTN_Y + 18, color=(255, 255, 255))

    # Hashtag footer
    f_tag = _font(bold, 28)
    tags  = "#dipfiyat  #amazon  #indirim  #shorts"
    _center_x(draw, tags, f_tag, y=BTN_Y + BTN_H + 20, color=(100, 140, 255), shadow=False)


# ─────────────────────────────────────────────────────────────
# Ana frame oluşturucu
# ─────────────────────────────────────────────────────────────

# Sahne zamanlaması (toplam 30 sn)
# 0.00 - 0.08  → Logo flash (header genişler)
# 0.08 - 0.35  → Ürün kartı iner
# 0.30 - 0.70  → Başlık / fiyat bilgisi açılır
# 0.65 - 1.00  → CTA butonu + loop (sürekli görünür)

def _make_frame(deal: dict, t: float, product_img) -> Image.Image:
    """t: 0.0 - 1.0 (normalize edilmiş zaman)"""
    bold  = config.FONT_PATH
    light = config.FONT_LIGHT_PATH if os.path.exists(config.FONT_LIGHT_PATH) else config.FONT_PATH

    canvas = Image.new("RGB", (W, H), (8, 8, 22))
    draw   = ImageDraw.Draw(canvas, "RGBA")

    t_sec = t * DURATION  # saniye cinsinden

    _draw_background(canvas, draw, t_sec)

    # Header — her zaman görünür, t < 0.08 ise genişleme animasyonu
    _draw_header(draw, t, bold, light)

    # Ürün kartı: 0.05'ten itibaren girer
    card_enter = _ease_out_cubic(max(0.0, (t - 0.05) / 0.25))
    card_bot   = _draw_product_card(canvas, draw, deal, product_img, card_enter, t_sec, bold, light)

    # Bilgi bölümü: 0.30'dan itibaren
    t_info = max(0.0, (t - 0.30) / 0.40)
    if t_info > 0:
        _draw_info_section(draw, deal, card_bot, t_info, bold, light)

    # CTA: 0.65'ten itibaren
    t_cta = max(0.0, t - 0.65)
    _draw_cta_button(draw, t_cta, bold)

    return canvas


# ─────────────────────────────────────────────────────────────
# Video olusturma
# ─────────────────────────────────────────────────────────────

def create_shorts_video(deal: dict) -> str | None:
    try:
        return _create_impl(deal)
    except Exception as e:
        logger.error("create_shorts_video hata [%s]: %s", deal.get("asin", "?"), e, exc_info=True)
        return None


def _create_impl(deal: dict) -> str | None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(FFMPEG):
        logger.error("FFmpeg bulunamadi: %s", FFMPEG)
        return None

    logger.info("Shorts video olusturuluyor: %s", deal.get("asin", "?"))

    product_img = _download_image(deal.get("image_url", ""))
    total_frames = FPS * DURATION

    tmp_dir = tempfile.mkdtemp(prefix="shorts_")
    try:
        logger.info("Frame render basliyor (%d frame, %d FPS)...", total_frames, FPS)
        for i in range(total_frames):
            t = i / total_frames
            frame = _make_frame(deal, t, product_img)
            frame.save(os.path.join(tmp_dir, f"frame_{i:05d}.png"))
            if i % 60 == 0:
                logger.info("  %d/%d frame tamamlandi", i, total_frames)

        asin      = deal.get("asin", "UNKNOWN")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path  = os.path.join(OUTPUT_DIR, f"short_{asin}_{timestamp}.mp4")

        # Müzik seç
        import glob as glob_mod
        music_dir    = os.path.dirname(config.MUSIC_PATH)
        music_files  = glob_mod.glob(os.path.join(music_dir, "*.mp3"))
        selected_music = random.choice(music_files) if music_files else None

        if selected_music:
            cmd = [
                FFMPEG, "-y",
                "-framerate", str(FPS),
                "-i", os.path.join(tmp_dir, "frame_%05d.png"),
                "-i", selected_music,
                "-c:v", "libx264",
                "-profile:v", "high",
                "-level", "4.2",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "slow",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-shortest",
                "-t", str(DURATION),
                "-movflags", "+faststart",
                out_path
            ]
        else:
            cmd = [
                FFMPEG, "-y",
                "-framerate", str(FPS),
                "-i", os.path.join(tmp_dir, "frame_%05d.png"),
                "-c:v", "libx264",
                "-profile:v", "high",
                "-level", "4.2",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                "-preset", "slow",
                "-t", str(DURATION),
                "-movflags", "+faststart",
                out_path
            ]

        logger.info("FFmpeg encode basliyor (preset=slow, crf=18)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            logger.error("FFmpeg hatasi:\n%s", result.stderr[-1000:])
            return None

        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        logger.info("Shorts video olusturuldu: %s (%.1f MB)", out_path, size_mb)
        return out_path

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────
# Hizli test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import io
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    test_deal = {
        "asin":           "B0DRSRH3GG",
        "title":          "QCY H3 Pro Hybrid ANC Hi-res LDAC Bluetooth 5.4 Kafaustu Kablosuz Kulaklik",
        "current_price":  1799.0,
        "original_price": 2999.0,
        "discount_pct":   40,
        "image_url":      "https://m.media-amazon.com/images/I/61CGHv6kmWL._AC_SL1500_.jpg",
    }

    path = create_shorts_video(test_deal)
    if path:
        print(f"Video olusturuldu: {path}")
        os.startfile(path)
    else:
        print("HATA: Video olusturulamadi!")
