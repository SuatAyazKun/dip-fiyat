"""
Merkezi yayın modülü.
Aynı görsel + caption'ı tüm kanallara gönderir:
  - Telegram Kanalı
  - Instagram (Graph API)
"""
import requests
import logging
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────

def _telegram_configured() -> bool:
    return (
        config.TELEGRAM_BOT_TOKEN
        and config.TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN"
        and config.TELEGRAM_CHANNEL_ID
        and config.TELEGRAM_CHANNEL_ID != "YOUR_CHANNEL_ID"
    )


def send_to_telegram(image_path: str, caption: str, affiliate_url: str = "") -> bool:
    """Görseli + caption'ı + 'Firsati Kacirma' butonunu Telegram kanalına gönderir."""
    if not _telegram_configured():
        logger.warning("Telegram ayarlanmamış, atlandı.")
        return False

    import json

    reply_markup = ""
    if affiliate_url:
        reply_markup = json.dumps({
            "inline_keyboard": [[
                {"text": "🛒  Firsati Kacirma!  Incele  ➜", "url": affiliate_url}
            ]]
        })

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as img_file:
            data = {
                "chat_id":    config.TELEGRAM_CHANNEL_ID,
                "caption":    caption[:1024],
                "parse_mode": "HTML",
            }
            if reply_markup:
                data["reply_markup"] = reply_markup

            resp = requests.post(url, data=data, files={"photo": img_file}, timeout=30)
        resp.raise_for_status()
        logger.info("Telegram kanalına gönderildi.")
        return True
    except Exception as e:
        logger.error("Telegram gönderim hatası: %s", e)
        return False


def notify_admin(message: str) -> bool:
    """Sadece bot sahibine (sizi) sistem mesajı gönderir."""
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        return False
    if not config.TELEGRAM_CHAT_ID or config.TELEGRAM_CHAT_ID == "YOUR_CHAT_ID":
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Admin bildirim hatası: %s", e)
        return False


# ─────────────────────────────────────────────
# INSTAGRAM  (Graph API)
# ─────────────────────────────────────────────

def _instagram_configured() -> bool:
    return (
        config.INSTAGRAM_USER_ID
        and config.INSTAGRAM_USER_ID != "YOUR_IG_USER_ID"
        and config.FACEBOOK_PAGE_TOKEN
        and config.FACEBOOK_PAGE_TOKEN != "YOUR_LONG_LIVED_TOKEN"
    )


def send_to_instagram(image_url: str, caption: str) -> bool:
    """Instagram Graph API ile görsel paylaşır."""
    if not _instagram_configured():
        logger.warning("Instagram ayarlanmamis, atlandi.")
        return False

    if not image_url:
        logger.warning("Instagram: image_url bos, atlandi.")
        return False

    base = f"https://graph.facebook.com/v21.0/{config.INSTAGRAM_USER_ID}"
    token = config.FACEBOOK_PAGE_TOKEN

    try:
        r = requests.post(f"{base}/media", data={
            "image_url": image_url,
            "caption":   caption[:2200],
            "access_token": token,
        }, timeout=30)
        r.raise_for_status()
        container_id = r.json().get("id")
        if not container_id:
            logger.error("Instagram container olusturulamadi: %s", r.json())
            return False

        r2 = requests.post(f"{base}/media_publish", data={
            "creation_id":  container_id,
            "access_token": token,
        }, timeout=30)
        r2.raise_for_status()
        post_id = r2.json().get("id")
        logger.info("Instagram'a gonderildi. Post ID: %s", post_id)
        return True

    except requests.exceptions.HTTPError as e:
        resp = e.response
        try:
            err = resp.json().get("error", {})
            code = err.get("code")
            subcode = err.get("error_subcode")
            msg = err.get("message", str(e))
            if code == 4 and subcode == 2207051:
                logger.error("Instagram API rate limit asildi (gunluk/saatlik limit). Birkaç saat bekleyin.")
            elif resp.status_code == 403:
                logger.error("Instagram 403 hatasi [kod=%s alt=%s]: %s", code, subcode, msg)
            else:
                logger.error("Instagram HTTP hatasi %s: %s", resp.status_code, msg)
        except Exception:
            logger.error("Instagram gonderim hatasi: %s", e)
        return False
    except Exception as e:
        logger.error("Instagram gonderim hatasi: %s", e)
        return False


# ─────────────────────────────────────────────
# ANA FONKSİYON — hepsine tek seferde gönder
# ─────────────────────────────────────────────

def send_video_to_telegram(video_path: str, caption: str, affiliate_url: str = "") -> bool:
    """Video dosyasını Telegram kanalına gönderir."""
    if not _telegram_configured():
        return False
    import json
    reply_markup = ""
    if affiliate_url:
        reply_markup = json.dumps({
            "inline_keyboard": [[
                {"text": "🛒  Firsati Kacirma!  Incele  ➜", "url": affiliate_url}
            ]]
        })
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(video_path, "rb") as vf:
            data = {
                "chat_id":    config.TELEGRAM_CHANNEL_ID,
                "caption":    caption[:1024],
                "parse_mode": "HTML",
            }
            if reply_markup:
                data["reply_markup"] = reply_markup
            resp = requests.post(url, data=data, files={"video": vf}, timeout=120)
        resp.raise_for_status()
        logger.info("Video Telegram kanalina gonderildi.")
        return True
    except Exception as e:
        logger.error("Telegram video gonderim hatasi: %s", e)
        return False


def send_video_to_instagram(video_path: str, caption: str) -> bool:
    """Video dosyasını GitHub'a yükleyip Instagram Reels olarak paylaşır."""
    if not _instagram_configured():
        return False
    try:
        from modules.github_pages import upload_image
        video_url = upload_image(video_path)
        if not video_url:
            logger.error("Video GitHub'a yuklenemedi.")
            return False

        base  = f"https://graph.facebook.com/v21.0/{config.INSTAGRAM_USER_ID}"
        token = config.FACEBOOK_PAGE_TOKEN

        r = requests.post(f"{base}/media", data={
            "media_type":   "REELS",
            "video_url":    video_url,
            "caption":      caption[:2200],
            "share_to_feed": "true",
            "access_token": token,
        }, timeout=60)
        r.raise_for_status()
        container_id = r.json().get("id")
        if not container_id:
            logger.error("Instagram video container olusturulamadi: %s", r.json())
            return False

        import time
        for _ in range(12):
            time.sleep(5)
            status_r = requests.get(f"https://graph.facebook.com/v21.0/{container_id}",
                                    params={"fields": "status_code", "access_token": token}, timeout=15)
            status = status_r.json().get("status_code", "")
            logger.info("Instagram video durumu: %s", status)
            if status == "FINISHED":
                break
            elif status == "ERROR":
                logger.error("Instagram video isleme hatasi.")
                return False

        r2 = requests.post(f"{base}/media_publish", data={
            "creation_id":  container_id,
            "access_token": token,
        }, timeout=30)
        r2.raise_for_status()
        logger.info("Instagram Reels gonderildi. Post ID: %s", r2.json().get("id"))
        return True
    except Exception as e:
        logger.error("Instagram video gonderim hatasi: %s", e)
        return False


def send_to_x(deal: dict, affiliate_url: str, image_path: str = "") -> bool:
    """X (Twitter)'a tweet atar."""
    try:
        from modules.x_poster import send_tweet
        return send_tweet(deal, affiliate_url, image_path)
    except Exception as e:
        logger.error("X gönderim hatası: %s", e)
        return False


def publish_all(image_path: str, caption: str, public_image_url: str = "", affiliate_url: str = "", deal: dict = None) -> dict:
    """
    Görseli tüm aktif kanallara gönderir.
    Döndürür: {"telegram": True/False, "instagram": True/False, "x": True/False}
    """
    results = {}

    results["telegram"] = send_to_telegram(image_path, caption, affiliate_url)

    from modules.github_pages import upload_image
    from modules.image_creator import create_instagram_image
    from modules.caption_writer import generate_instagram
    ig_local     = create_instagram_image(deal) if deal else None
    ig_upload    = upload_image(ig_local) if ig_local else upload_image(image_path) if image_path else ""
    ig_image_url = ig_upload or public_image_url
    ig_caption   = generate_instagram(deal) if deal else caption
    results["instagram"] = send_to_instagram(ig_image_url, ig_caption) if ig_image_url else False

    # X (Twitter)
    if deal and affiliate_url:
        results["x"] = send_to_x(deal, affiliate_url, image_path)
    else:
        results["x"] = False

    basarili  = [k for k, v in results.items() if v]
    basarisiz = [k for k, v in results.items() if not v]

    if basarili:
        notify_admin(
            f"✅ <b>Yayınlandı!</b>\n"
            f"Kanallar: {', '.join(basarili)}\n"
            + (f"⚠️ Başarısız: {', '.join(basarisiz)}" if basarisiz else "")
        )
    else:
        notify_admin("❌ Hiçbir kanala gönderilemedi!")

    return results


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    ok = notify_admin("🔔 <b>Dip Fiyat</b> — publisher.py test mesajı, sistem çalışıyor!")
    print("Admin bildirimi:", "OK" if ok else "Ayarlanmamış (config.py doldurun)")

    test_image = r"C:\Software\amz\output\images"
    images = [f for f in os.listdir(test_image) if f.endswith(".png")] if os.path.exists(test_image) else []
    if images:
        latest = os.path.join(test_image, sorted(images)[-1])
        print(f"Test görseli: {latest}")
        result = send_to_telegram(latest, "🔔 Bu bir test paylaşımıdır — Dip Fiyat sistemi!")
        print("Telegram kanal gönderimi:", "OK" if result else "Başarısız veya ayarlanmamış")
    else:
        print("Test görseli bulunamadı. Önce image_creator.py çalıştırın.")
