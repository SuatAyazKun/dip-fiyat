"""
Dip Fiyat — Ana Pipeline
Kullanim:
  Otomatik (3 firsat bulur, 3'unu de gonderir):
    python scheduler.py
  Belirli bir urun:
    python scheduler.py https://www.amazon.com.tr/dp/ASIN
"""
import sys
import os
import time
import logging
import logging.handlers
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from modules.amazon_scraper import fetch_product  # URL ile manuel gönderim için
from modules.deal_finder     import get_top_deals
from modules.image_creator   import create_image
from modules.caption_writer  import generate as generate_caption, build_affiliate_url
from modules.publisher       import publish_all, notify_admin
from modules.database        import init_db, is_recently_posted, mark_posted, start_run, finish_run
from modules.github_pages    import update_page, get_recent_deals_for_page

# --- Loglama ---
os.makedirs(os.path.dirname(config.LOG_PATH), exist_ok=True)
handler = logging.handlers.RotatingFileHandler(
    config.LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[handler, logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _post_single(deal: dict, custom_affiliate_url: str = "") -> bool:
    """Tek bir urunu gorselle birlikte tum kanallara gonderir."""
    try:
        logger.info("Urun: %s", deal["title"][:60])
        logger.info("Fiyat: %.0f TL  |  Indirim: %%%.0f", deal["current_price"], deal["discount_pct"])

        # Daha once paylasildiysa atla
        if is_recently_posted(deal["asin"]):
            logger.info("Atlandi (son %d gun paylasildi): %s", config.REPOST_DAYS, deal["asin"])
            return False

        # Gorsel olustur
        logger.info("Gorsel olusturuluyor...")
        image_path = create_image(deal)
        if not image_path:
            logger.error("Gorsel olusturulamadi: %s", deal["asin"])
            return False
        logger.info("Gorsel hazir: %s", os.path.basename(image_path))

        # Affiliate link — kullanicinin verdigi link varsa onu kullan
        affiliate_url = custom_affiliate_url if custom_affiliate_url else build_affiliate_url(deal["asin"])
        caption       = generate_caption(deal, affiliate_url)

        # Yayinla — WhatsApp icin Amazon gorsel URL'ini kullan
        amazon_image_url = deal.get("image_url", "")
        logger.info("Yayinlaniyor...")
        results   = publish_all(image_path=image_path, caption=caption,
                                affiliate_url=affiliate_url, public_image_url=amazon_image_url,
                                deal=deal)
        posted_ok = any(results.values())

        if posted_ok:
            mark_posted(
                asin=deal["asin"],
                title=deal["title"],
                discount_pct=deal["discount_pct"],
                original_price=deal["original_price"],
                sale_price=deal["current_price"],
                video_path=image_path,
                image_url=deal.get("image_url", ""),
            )
            logger.info("Kaydedildi ve gonderildi: %s", deal["asin"])
        else:
            logger.error("Hicbir kanala gonderilemedi: %s", deal["asin"])

        return posted_ok

    except Exception as e:
        logger.error("_post_single beklenmedik hata [%s]: %s", deal.get("asin", "?"), e, exc_info=True)
        return False


def run(url_or_asin: str = "", affiliate_url: str = "") -> bool:
    run_id = start_run()
    logger.info("=" * 55)
    logger.info("Pipeline basladi  —  %s", datetime.now().strftime("%d.%m.%Y %H:%M"))

    # ── ELLE VERİLEN URL / ASIN ─────────────────────────────
    if url_or_asin:
        logger.info("Elle girilen urun: %s", url_or_asin)
        deal = fetch_product(url_or_asin)
        if not deal or deal.get("current_price", 0) == 0:
            msg = "Urun bilgisi alinamadi."
            logger.error(msg)
            notify_admin(f"❌ {msg}")
            finish_run(run_id, deals_found=0, posted=0, error=msg)
            return False
        ok = _post_single(deal, custom_affiliate_url=affiliate_url)
        finish_run(run_id, deals_found=1, posted=1 if ok else 0)
        # GitHub Pages guncelle
        if ok:
            logger.info("GitHub Pages guncelleniyor...")
            update_page(get_recent_deals_for_page(limit=50))
        logger.info("Pipeline tamamlandi.")
        return ok

    # ── OTOMATİK: FIRSAT BUL, HEPSINI GÖNDER ───────────────
    logger.info("Otomatik firsat aranıyor...")
    candidates = get_top_deals(limit=3)

    if not candidates:
        msg = "Uygun firsat bulunamadi."
        logger.warning(msg)
        notify_admin(f"ℹ️ {msg}")
        finish_run(run_id, deals_found=0, posted=0)
        return False

    logger.info("%d firsat bulundu, tumu gonderiliyor.", len(candidates))

    posted_count = 0
    for i, candidate in enumerate(candidates, 1):
        logger.info("[ %d / %d ] isleniyor...", i, len(candidates))
        ok = _post_single(candidate)
        if ok:
            posted_count += 1
        if i < len(candidates):
            logger.info("Sonraki gonderi icin 60 saniye bekleniyor...")
            time.sleep(60)

    finish_run(run_id, deals_found=len(candidates), posted=posted_count)

    # GitHub Pages guncelle
    if posted_count > 0:
        logger.info("GitHub Pages guncelleniyor...")
        deals_for_page = get_recent_deals_for_page(limit=50)
        update_page(deals_for_page)
        notify_admin(f"✅ {posted_count} firsat gonderildi. Sayfa guncellendi.")
    else:
        notify_admin("❌ Hicbir urun gonderilemedi.")

    logger.info("Pipeline tamamlandi. Gonderilen: %d / %d", posted_count, len(candidates))
    return posted_count > 0


if __name__ == "__main__":
    import msvcrt

    lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pipeline.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        logger.warning("Pipeline zaten calisıyor, ikinci istek reddedildi.")
        sys.exit(0)

    try:
        init_db()
        url           = sys.argv[1] if len(sys.argv) > 1 else ""
        affiliate_url = sys.argv[2] if len(sys.argv) > 2 else ""
        ok  = run(url, affiliate_url)
    finally:
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        lock_file.close()

    sys.exit(0 if ok else 1)
