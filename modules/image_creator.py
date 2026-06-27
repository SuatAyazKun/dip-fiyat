"""
Urun firsati icin Instagram paylasim gorseli uretir.
Format: 1080x1920 px (9:16), acik/beyaz tema.
Cikti: output/images/ klasorunde PNG dosyasi.
"""
import os
import sys
import requests
import logging
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

W, H       = 1080, 1920
MARGIN     = 48

# Renkler
BG         = (247, 248, 252)
CARD       = (255, 255, 255)
HEADER_BG  = (255, 75, 0)
HEADER_FG  = (255, 255, 255)
SLOGAN_FG  = (255, 210, 190)
TITLE_FG   = (25,  25,  35)
PRICE_FG   = (0,   155, 60)
OLD_FG     = (190, 20,  20)
BADGE_BG   = (255, 75,  0)
BADGE_FG   = (255, 255, 255)
INFO_FG    = (70,  70,  85)
DIVIDER    = (215, 215, 222)
TAG_FG     = (0,   95,  200)
DATE_FG    = (160, 160, 170)
SELLER_FG  = (50,  50,  50)

OUTPUT_DIR = os.path.join(config.BASE_DIR, "output", "images")


def _dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _tw(text: str, font, draw: ImageDraw.ImageDraw) -> float:
    try:
        return draw.textlength(text, font=font)
    except Exception:
        b = font.getbbox(text)
        return b[2] - b[0]


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list:
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


def _rrect(draw, xy, r, fill):
    draw.rounded_rectangle(xy, radius=r, fill=fill)


def _center_text(draw, text, font, y, color, x0=0, x1=W):
    w = _tw(text, font, draw)
    draw.text(((x0 + x1 - w) / 2, y), text, font=font, fill=color)


def _download_image(url: str):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as e:
        logger.error("Gorsel indirilemedi: %s", e)
        return None


def create_image(deal: dict) -> str | None:
    """Telegram için dikey (1080x1920) görsel oluşturur."""
    try:
        return _create_image_impl(deal)
    except Exception as e:
        logger.error("create_image beklenmedik hata [%s]: %s", deal.get("asin", "?"), e, exc_info=True)
        return None


def create_instagram_image(deal: dict) -> str | None:
    """Instagram için kare (1080x1080) görsel oluşturur."""
    try:
        return _create_instagram_impl(deal)
    except Exception as e:
        logger.error("create_instagram_image hata [%s]: %s", deal.get("asin", "?"), e, exc_info=True)
        return None


def _create_instagram_impl(deal: dict) -> str | None:
    _dir()
    S    = 1080
    M    = 48
    reg  = config.FONT_LIGHT_PATH if os.path.exists(config.FONT_LIGHT_PATH) else config.FONT_PATH
    bold = config.FONT_PATH

    f_logo  = _font(bold, 58)
    f_title = _font(bold, 40)
    f_price = _font(bold, 90)
    f_old   = _font(reg,  36)
    f_badge = _font(bold, 36)

    canvas = Image.new("RGB", (S, S), (255, 255, 255))
    draw   = ImageDraw.Draw(canvas)

    # ── HEADER (ince) ─────────────────────────────────────────
    HDR_H = 80
    draw.rectangle([0, 0, S, HDR_H], fill=(255, 75, 0))
    _center_text(draw, "DIP FIYAT", f_logo, y=10, color=(255, 255, 255), x0=0, x1=S)

    # ── ÜRÜN GÖRSELİ (büyük, ortada) ─────────────────────────
    IMG_TOP = HDR_H
    IMG_H   = 540
    IMG_BOT = IMG_TOP + IMG_H
    draw.rectangle([0, IMG_TOP, S, IMG_BOT], fill=(248, 248, 250))

    product_img = _download_image(deal.get("image_url", ""))
    if product_img:
        product_img.thumbnail((S - 60, IMG_H - 30), Image.LANCZOS)
        px = (S - product_img.width) // 2
        py = IMG_TOP + (IMG_H - product_img.height) // 2
        if product_img.mode == "RGBA":
            canvas.paste(product_img, (px, py), product_img)
        else:
            canvas.paste(product_img, (px, py))

    # ── ALT BÖLÜM (beyaz arka plan) ───────────────────────────
    y = IMG_BOT + 20

    # İndirim rozeti — büyük, solda
    disc = deal.get("discount_pct", 0)
    if disc >= 1:
        bt = f"%{int(disc)} İNDİRİM"
        bw = int(_tw(bt, f_badge, draw)) + 40
        bh = 54
        _rrect(draw, [M, y, M + bw, y + bh], r=12, fill=(255, 75, 0))
        draw.text((M + 20, y + 9), bt, font=f_badge, fill=(255, 255, 255))
        y += bh + 18

    # Başlık
    title = deal.get("title", "")
    lines = _wrap(title, f_title, S - M * 2, draw)[:2]
    if len(_wrap(title, f_title, S - M * 2, draw)) > 2:
        lines[-1] = lines[-1][:max(1, len(lines[-1]) - 3)] + "..."
    for line in lines:
        draw.text((M, y), line, font=f_title, fill=(25, 25, 35))
        y += 48
    y += 10

    # Eski fiyat ve yeni fiyat yan yana
    cur  = deal.get("current_price", 0)
    orig = deal.get("original_price", 0)

    if orig and orig > cur:
        old_str = f"{orig:,.0f} TL".replace(",", ".")
        ow = _tw(old_str, f_old, draw)
        ox = (S - ow) // 2
        draw.text((ox, y), old_str, font=f_old, fill=(180, 180, 180))
        draw.line([(ox, y + 21), (ox + int(ow), y + 21)], fill=(180, 180, 180), width=2)
        y += 44

    price_str = f"{cur:,.0f} TL".replace(",", ".")
    pw = _tw(price_str, f_price, draw)
    draw.text(((S - pw) // 2, y), price_str, font=f_price, fill=(0, 155, 60))
    y += 100

    # Alt boşluğu kırp
    final_h = min(y + 10, S)
    canvas = canvas.crop((0, 0, S, final_h))

    asin      = deal.get("asin", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = os.path.join(OUTPUT_DIR, f"ig_{asin}_{timestamp}.png")
    canvas.save(filepath, "PNG")
    logger.info("Instagram gorseli olusturuldu: %s", filepath)
    return filepath


def _create_image_impl(deal: dict) -> str | None:
    _dir()

    reg  = config.FONT_LIGHT_PATH if os.path.exists(config.FONT_LIGHT_PATH) else config.FONT_PATH
    bold = config.FONT_PATH

    f_logo    = _font(bold, 82)
    f_slogan  = _font(reg,  32)
    f_title   = _font(bold, 50)
    f_price   = _font(bold, 100)
    f_old     = _font(reg,  40)
    f_badge   = _font(bold, 34)
    f_info    = _font(reg,  38)
    f_info_b  = _font(bold, 38)
    f_tag     = _font(reg,  28)
    f_date    = _font(reg,  26)

    canvas = Image.new("RGB", (W, H), BG)
    draw   = ImageDraw.Draw(canvas)

    # ── 1. HEADER ────────────────────────────────────────────────────────
    HDR_H = 155
    draw.rectangle([0, 0, W, HDR_H], fill=HEADER_BG)

    logo = "DIP FIYAT"
    _center_text(draw, logo, f_logo, y=14, color=HEADER_FG)

    slogan = "Amazon'un En Iyi Firsatlari"
    _center_text(draw, slogan, f_slogan, y=HDR_H - 44, color=SLOGAN_FG)

    # ── 2. URUN GORSELI KARTI ────────────────────────────────────────────
    IMG_TOP = HDR_H + 28
    IMG_H   = 680
    IMG_BOT = IMG_TOP + IMG_H
    cm      = MARGIN

    _rrect(draw, [cm, IMG_TOP, W - cm, IMG_BOT], r=20, fill=CARD)

    product_img = _download_image(deal.get("image_url", ""))
    if product_img:
        max_w = W - cm * 2 - 60
        max_h = IMG_H - 40
        product_img.thumbnail((max_w, max_h), Image.LANCZOS)
        px = (W - product_img.width) // 2
        py = IMG_TOP + (IMG_H - product_img.height) // 2
        if product_img.mode == "RGBA":
            canvas.paste(product_img, (px, py), product_img)
        else:
            canvas.paste(product_img, (px, py))

    # Indirim rozeti
    disc = deal.get("discount_pct", 0)
    if disc >= 1:
        bt   = f"%{int(disc)} INDIRIM"
        bw   = int(_tw(bt, f_badge, draw)) + 44
        bh   = 58
        bx   = W - cm - bw - 10
        by   = IMG_TOP + 14
        _rrect(draw, [bx, by, bx + bw, by + bh], r=12, fill=BADGE_BG)
        tw   = _tw(bt, f_badge, draw)
        draw.text((bx + (bw - tw) / 2, by + 10), bt, font=f_badge, fill=BADGE_FG)

    # ── 3. URUN ADI ──────────────────────────────────────────────────────
    title     = deal.get("title", "")
    t_top     = IMG_BOT + 30
    lines     = _wrap(title, f_title, W - MARGIN * 2, draw)[:3]
    for i, line in enumerate(lines):
        draw.text((MARGIN, t_top + i * 60), line, font=f_title, fill=TITLE_FG)
    t_bot = t_top + len(lines) * 60 + 10

    # ── 4. FIYAT BLOGU ───────────────────────────────────────────────────
    p_top = t_bot + 22

    cur  = deal.get("current_price", 0)
    orig = deal.get("original_price", 0)

    # Yeni fiyat
    price_str = f"{cur:,.0f} TL".replace(",", ".")
    draw.text((MARGIN, p_top), price_str, font=f_price, fill=PRICE_FG)
    p_bot = p_top + 108

    # Eski fiyat (varsa)
    if orig and orig > cur:
        old_str = f"Normal Fiyat: {orig:,.0f} TL".replace(",", ".")
        draw.text((MARGIN, p_bot), old_str, font=f_old, fill=OLD_FG)
        ow    = _tw(old_str, f_old, draw)
        mid_y = int(p_bot + 22)
        draw.line([(MARGIN, mid_y), (MARGIN + int(ow), mid_y)], fill=OLD_FG, width=3)
        p_bot += 52

    # ── 5. AYIRICI ───────────────────────────────────────────────────────
    div_y = p_bot + 20
    draw.line([(MARGIN, div_y), (W - MARGIN, div_y)], fill=DIVIDER, width=2)

    # ── 6. BILGI SATIRLARI ───────────────────────────────────────────────
    inf_y   = div_y + 24
    row_h   = 56

    def info_row(y, label, value, label_color=INFO_FG, value_color=SELLER_FG):
        draw.text((MARGIN, y), label, font=f_info_b, fill=label_color)
        lw = _tw(label, f_info_b, draw)
        draw.text((MARGIN + lw + 8, y), value, font=f_info, fill=value_color)

    # Durum
    condition = deal.get("condition", "").strip()
    if condition:
        info_row(inf_y, "Durum:", condition)
        inf_y += row_h

    # Satici
    seller = deal.get("seller", "").strip()
    if seller:
        info_row(inf_y, "Satici:", seller)
        inf_y += row_h

    # Stok
    stock = deal.get("stock_note", "").strip()
    if stock:
        info_row(inf_y, "Stok:", stock, label_color=(190, 80, 0))
        inf_y += row_h + 8

    # ── FIRSAT BUTONU ────────────────────────────────────────────────────
    btn_h  = 90
    btn_y  = inf_y + 10
    _rrect(draw, [MARGIN, btn_y, W - MARGIN, btn_y + btn_h], r=18, fill=HEADER_BG)
    f_btn  = _font(bold, 48)
    btn_txt = "Firsati Kacirma  Incele  >"
    _center_text(draw, btn_txt, f_btn, y=btn_y + 20, color=(255, 255, 255))
    inf_y = btn_y + btn_h + 16

    # ── 7. FOOTER ────────────────────────────────────────────────────────
    footer_y = H - 110
    draw.line([(0, footer_y), (W, footer_y)], fill=DIVIDER, width=1)

    tags = "#dipfiyat  #amazon  #amazontrkiye  #indirim  #kampanya  #firsat"
    _center_text(draw, tags, f_tag, y=footer_y + 18, color=TAG_FG)

    ts = datetime.now().strftime("%d.%m.%Y")
    _center_text(draw, ts, f_date, y=footer_y + 68, color=DATE_FG)

    # Sol alt köşe — işbirliği etiketi
    draw.text((MARGIN, footer_y + 68), "#İşbirliği", font=f_date, fill=(150, 150, 160))

    # ── 8. KAYDET ────────────────────────────────────────────────────────
    asin      = deal.get("asin", "UNKNOWN")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = os.path.join(OUTPUT_DIR, f"deal_{asin}_{timestamp}.png")
    canvas.save(filepath, "PNG")
    logger.info("Gorsel olusturuldu: %s", filepath)
    return filepath


# ── TEST ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_deal = {
        "title":          "QCY H3 Pro Hybrid ANC Hi-res LDAC Bluetooth 5.4 Kafaustu Kablosuz Kulaklik Cift Cihaz destegi Siyah",
        "current_price":  1506,
        "original_price": 2499,
        "discount_pct":   40,
        "image_url":      "https://m.media-amazon.com/images/I/61CGHv6kmWL._AC_SL1500_.jpg",
        "condition":      "Ikinci El: Yeni Gibi",
        "stock_note":     "Stokta sadece 1 adet kaldi.",
        "seller":         "Amazon Depo",
        "asin":           "B0DRSRH3GG",
    }

    path = create_image(test_deal)
    if path:
        print("Gorsel olusturuldu:", path)
        os.startfile(path)
    else:
        print("Gorsel olusturulamadi!")
