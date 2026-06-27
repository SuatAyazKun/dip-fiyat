"""
Instagram Reels icin 9:16 dikey video olusturur.
Giris: deal dict + urun gorseli
Cikis: output/videos/ klasorunde MP4 dosyasi
"""
import os
import sys
import subprocess
import logging
import requests
import tempfile
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

W, H       = 1080, 1920
FPS        = 30
DURATION   = 15  # saniye
FFMPEG     = config.FFMPEG_PATH
OUTPUT_DIR = os.path.join(config.BASE_DIR, "output", "videos")
MUSIC_PATH = config.MUSIC_PATH


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _tw(text: str, font, draw) -> float:
    try:
        return draw.textlength(text, font=font)
    except Exception:
        b = font.getbbox(text)
        return b[2] - b[0]


def _center_text(draw, text, font, y, color, x0=0, x1=W):
    w = _tw(text, font, draw)
    draw.text(((x0 + x1 - w) / 2, y), text, font=font, fill=color)


def _wrap(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if _tw(test, font, draw) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _download_image(url: str):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        logger.error("Gorsel indirilemedi: %s", e)
        return None


def _ease_out(x: float) -> float:
    return 1 - (1 - x) ** 3


def _ease_in_out(x: float) -> float:
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def _make_frame(deal: dict, t: float, product_img) -> Image.Image:
    """t: 0.0 - 1.0 arasi zaman"""
    reg  = config.FONT_LIGHT_PATH if os.path.exists(config.FONT_LIGHT_PATH) else config.FONT_PATH
    bold = config.FONT_PATH

    f_logo  = _font(bold, 100)
    f_sub   = _font(reg,   38)
    f_title = _font(bold,  54)
    f_price = _font(bold, 130)
    f_old   = _font(reg,   46)
    f_badge = _font(bold,  44)
    f_cta   = _font(bold,  56)
    f_tag   = _font(reg,   30)

    # ── 5 sahne: her biri ~0.2 ────────────────────────────────
    # 0.00-0.12 → Logo flash
    # 0.12-0.35 → Ürün görseli çarpar
    # 0.35-0.58 → Başlık satırları fırlar
    # 0.58-0.80 → Fiyat patlar
    # 0.80-1.00 → CTA yanıp söner

    canvas = Image.new("RGB", (W, H), (10, 10, 18))
    draw   = ImageDraw.Draw(canvas)

    # Arka plan — diagonal çizgiler (enerji hissi)
    for i in range(0, W + H, 80):
        draw.line([(i, 0), (i - H, H)], fill=(20, 20, 35), width=2)

    # ── SAHNE 1: Logo flash (0.00 - 0.12) ─────────────────────
    HDR_H = 170
    if t < 0.12:
        progress = _ease_out(t / 0.12)
        # Header sola-sağa genişler
        hw = int(W * progress)
        hx = (W - hw) // 2
        draw.rectangle([hx, 0, hx + hw, HDR_H], fill=(255, 75, 0))
        if progress > 0.5:
            logo_scale = _ease_out((progress - 0.5) / 0.5)
            logo_y = int(HDR_H // 2 - 45 - (1 - logo_scale) * 30)
            _center_text(draw, "DIP FIYAT", f_logo, y=logo_y, color=(255, 255, 255))
    else:
        draw.rectangle([0, 0, W, HDR_H], fill=(255, 75, 0))
        _center_text(draw, "DIP FIYAT", f_logo, y=HDR_H // 2 - 45, color=(255, 255, 255))
        _center_text(draw, "Amazon'un En Iyi Firsatlari", f_sub, y=HDR_H - 50, color=(255, 210, 190))

    # ── SAHNE 2: Ürün görseli çarpar (0.12 - 0.35) ────────────
    IMG_TOP = HDR_H + 20
    IMG_H   = 720
    IMG_BOT = IMG_TOP + IMG_H

    if t >= 0.12:
        progress = min(1.0, _ease_out((t - 0.12) / 0.15))
        # Yukarıdan hızlıca düşer + bounce
        bounce = 0
        if t < 0.27:
            p2 = (t - 0.12) / 0.15
            bounce = int(math.sin(p2 * math.pi) * 30 * (1 - p2))

        card_top = IMG_TOP - int((1 - progress) * 400) + bounce
        draw.rounded_rectangle(
            [36, card_top, W - 36, card_top + IMG_H],
            radius=28, fill=(255, 255, 255)
        )

        if product_img:
            pi = product_img.copy()
            pi.thumbnail((W - 100, IMG_H - 30), Image.LANCZOS)
            px = (W - pi.width) // 2
            py = card_top + (IMG_H - pi.height) // 2
            if pi.mode == "RGBA":
                canvas.paste(pi, (px, py), pi)
            else:
                canvas.paste(pi, (px, py))

        # İndirim rozeti — sağdan fırlar
        disc = deal.get("discount_pct", 0)
        if disc >= 1 and progress > 0.5:
            badge_p = _ease_out((progress - 0.5) / 0.5)
            pulse   = 1.0 + 0.08 * math.sin(t * 25)
            bt  = f"%{int(disc)} INDIRIM"
            bw  = int(_tw(bt, f_badge, draw) * pulse) + 50
            bh  = int(68 * pulse)
            bx  = W - 52 - bw + int((1 - badge_p) * 300)
            by  = card_top + 18
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16, fill=(255, 75, 0))
            # Parlama efekti
            draw.rounded_rectangle([bx, by, bx + bw, by + bh // 2], radius=16, fill=(255, 110, 40))
            tw = _tw(bt, f_badge, draw)
            draw.text((bx + (bw - tw) / 2, by + 12), bt, font=f_badge, fill=(255, 255, 255))

    # ── SAHNE 3: Başlık satırları fırlar (0.35 - 0.58) ────────
    if t >= 0.35:
        title = deal.get("title", "")
        lines = _wrap(title, f_title, W - 96, draw)[:2]
        for i, line in enumerate(lines):
            line_t = (t - 0.35 - i * 0.06) / 0.10
            p = max(0.0, min(1.0, _ease_out(line_t)))
            offset = int((1 - p) * 150)
            draw.text((48 + offset, IMG_BOT + 30 + i * 68), line,
                      font=f_title, fill=(255, 255, 255))

    # ── SAHNE 4: Fiyat patlar (0.58 - 0.80) ───────────────────
    if t >= 0.58:
        cur  = deal.get("current_price", 0)
        orig = deal.get("original_price", 0)
        p    = min(1.0, _ease_out((t - 0.58) / 0.12))
        title_lines = min(2, len(_wrap(deal.get("title",""), f_title, W-96, draw)))
        p_y  = IMG_BOT + 30 + title_lines * 68 + 20

        if orig and orig > cur:
            scale = 0.5 + 0.5 * p
            old_str = f"Normal: {orig:,.0f} TL".replace(",", ".")
            draw.text((48, p_y), old_str, font=f_old, fill=(220, 80, 80))
            ow = _tw(old_str, f_old, draw)
            draw.line([(48, p_y + 26), (48 + int(ow), p_y + 26)], fill=(220, 80, 80), width=3)
            p_y += 60

        # Fiyat zoom ile gelir
        price_str = f"{cur:,.0f} TL".replace(",", ".")
        pw = _tw(price_str, f_price, draw)
        px_pos = (W - pw) // 2
        # Büyükten küçüğe zoom
        zoom = 1.4 - 0.4 * p
        if zoom != 1.0:
            tmp = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
            td  = ImageDraw.Draw(tmp)
            td.text((px_pos, 10), price_str, font=f_price, fill=(40, 230, 100))
            new_w = int(W * zoom)
            new_h = int(160 * zoom)
            tmp = tmp.resize((new_w, new_h), Image.LANCZOS)
            ox = (W - new_w) // 2
            oy = p_y - int((new_h - 160) / 2)
            canvas.paste(tmp, (ox, oy), tmp)
        else:
            draw.text((px_pos, p_y), price_str, font=f_price, fill=(40, 230, 100))

    # ── SAHNE 5: CTA yanıp söner (0.80 - 1.00) ────────────────
    if t >= 0.80:
        p     = min(1.0, _ease_out((t - 0.80) / 0.10))
        blink = 0.75 + 0.25 * abs(math.sin(t * 12))
        r     = int(255 * blink)
        g     = int(75 * blink)
        btn_y = H - 200
        # Aşağıdan fırlar
        btn_y_anim = btn_y + int((1 - p) * 150)
        draw.rounded_rectangle([44, btn_y_anim, W - 44, btn_y_anim + 100],
                                radius=22, fill=(r, g, 0))
        # Buton parlaması
        draw.rounded_rectangle([44, btn_y_anim, W - 44, btn_y_anim + 50],
                                radius=22, fill=(min(255, r + 30), min(110, g + 35), 0))
        _center_text(draw, "Firsati Kacirma!", f_cta, y=btn_y_anim + 20, color=(255, 255, 255))

    # Footer hashtag
    tags = "#dipfiyat  #amazon  #indirim  #kampanya"
    _center_text(draw, tags, f_tag, y=H - 55, color=(100, 140, 255))

    return canvas


def create_video(deal: dict) -> str | None:
    try:
        return _create_video_impl(deal)
    except Exception as e:
        logger.error("create_video hata [%s]: %s", deal.get("asin", "?"), e, exc_info=True)
        return None


def _create_video_impl(deal: dict) -> str | None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(FFMPEG):
        logger.error("FFmpeg bulunamadi: %s", FFMPEG)
        return None

    logger.info("Video olusturuluyor: %s", deal.get("asin", "?"))

    # Ürün görselini indir
    product_img = _download_image(deal.get("image_url", ""))

    total_frames = FPS * DURATION
    tmp_dir = tempfile.mkdtemp()

    try:
        # Frame'leri oluştur
        logger.info("Frameler olusturuluyor (%d frame)...", total_frames)
        for i in range(total_frames):
            t = i / total_frames
            frame = _make_frame(deal, t, product_img)
            frame.save(os.path.join(tmp_dir, f"frame_{i:04d}.png"))

        asin      = deal.get("asin", "UNKNOWN")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path  = os.path.join(OUTPUT_DIR, f"reels_{asin}_{timestamp}.mp4")

        # FFmpeg ile video oluştur
        # Rastgele müzik seç
        import random, glob
        music_files = glob.glob(os.path.join(os.path.dirname(MUSIC_PATH), "*.mp3"))
        selected_music = random.choice(music_files) if music_files else None
        if selected_music:
            logger.info("Muzik secildi: %s", os.path.basename(selected_music))

        if selected_music:
            cmd = [
                FFMPEG, "-y",
                "-framerate", str(FPS),
                "-i", os.path.join(tmp_dir, "frame_%04d.png"),
                "-i", selected_music,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "23",
                "-preset", "fast",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                "-t", str(DURATION),
                out_path
            ]
        else:
            cmd = [
                FFMPEG, "-y",
                "-framerate", str(FPS),
                "-i", os.path.join(tmp_dir, "frame_%04d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "23",
                "-preset", "fast",
                "-t", str(DURATION),
                out_path
            ]

        logger.info("FFmpeg calistiriliyor...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("FFmpeg hatasi: %s", result.stderr[-500:])
            return None

        logger.info("Video olusturuldu: %s", out_path)
        return out_path

    finally:
        # Temp dosyaları temizle
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    import io
    logging.basicConfig(level=logging.INFO)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    test_deal = {
        "asin":           "B0DRSRH3GG",
        "title":          "QCY H3 Pro Hybrid ANC Hi-res LDAC Bluetooth 5.4 Kafaustu Kablosuz Kulaklik",
        "current_price":  1799.0,
        "original_price": 2999.0,
        "discount_pct":   40,
        "image_url":      "https://m.media-amazon.com/images/I/61CGHv6kmWL._AC_SL1500_.jpg",
    }

    path = create_video(test_deal)
    if path:
        print("Video olusturuldu:", path)
        os.startfile(path)
    else:
        print("Video olusturulamadi!")
