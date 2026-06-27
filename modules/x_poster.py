"""
X (Twitter) API v2 ile otomatik tweet atar.
Free plan: metin + link (görsel yok)
Basic plan ($100/ay): görsel ekleme aktif olur
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

# Tweet karakter limiti (URL 23 karakter sayılır)
_TWEET_LIMIT = 280


def _configured() -> bool:
    required = [
        config.X_API_KEY,
        config.X_API_SECRET,
        config.X_ACCESS_TOKEN,
        config.X_ACCESS_TOKEN_SECRET,
    ]
    placeholders = {"YOUR_X_API_KEY", "YOUR_X_API_SECRET",
                    "YOUR_X_ACCESS_TOKEN", "YOUR_X_ACCESS_TOKEN_SECRET"}
    return all(v and v not in placeholders for v in required)


def _get_client():
    try:
        import tweepy
    except ImportError:
        raise ImportError("tweepy kurulu değil. Çalıştırın: pip install tweepy")

    return tweepy.Client(
        consumer_key=config.X_API_KEY,
        consumer_secret=config.X_API_SECRET,
        access_token=config.X_ACCESS_TOKEN,
        access_token_secret=config.X_ACCESS_TOKEN_SECRET,
    )


def _get_v1_api():
    """Görsel yükleme için v1.1 API (Basic plan gerekir)."""
    try:
        import tweepy
    except ImportError:
        raise ImportError("tweepy kurulu değil. Çalıştırın: pip install tweepy")

    auth = tweepy.OAuth1UserHandler(
        config.X_API_KEY,
        config.X_API_SECRET,
        config.X_ACCESS_TOKEN,
        config.X_ACCESS_TOKEN_SECRET,
    )
    return tweepy.API(auth)


def _build_tweet(deal: dict, affiliate_url: str) -> str:
    title         = deal.get("title", "")
    current_price = deal.get("current_price", 0)
    original_price = deal.get("original_price", 0)
    discount_pct  = deal.get("discount_pct", 0)
    stock_note    = deal.get("stock_note", "")

    hashtags = "#dipfiyat #amazon #indirim #fırsat #kampanya"

    lines = []
    lines.append(f"🔥 {title[:100]}{'...' if len(title) > 100 else ''}")
    lines.append("")

    if original_price and original_price > current_price:
        lines.append(f"❌ {original_price:,.0f} TL → 💰 {current_price:,.0f} TL".replace(",", "."))
    else:
        lines.append(f"💰 {current_price:,.0f} TL".replace(",", "."))

    if discount_pct >= 1:
        lines.append(f"💥 %{int(discount_pct)} İndirim!")

    if stock_note and ("kaldı" in stock_note.lower() or "son" in stock_note.lower()):
        lines.append(f"⚡ {stock_note[:50]}")

    lines.append("")
    lines.append(f"👉 {affiliate_url}")
    lines.append("")
    lines.append("🌐 Tüm indirimler → dipfiyatci.com")
    lines.append("")
    lines.append(hashtags)

    tweet = "\n".join(lines)

    # Karakter limitini aşarsa başlığı kısalt
    if len(tweet) > _TWEET_LIMIT:
        overflow = len(tweet) - _TWEET_LIMIT + 3
        short_title = title[:max(10, 100 - overflow)] + "..."
        lines[0] = f"🔥 {short_title}"
        tweet = "\n".join(lines)

    return tweet


def send_tweet(deal: dict, affiliate_url: str, image_path: str = "") -> bool:
    """
    Fırsatı X'e tweet olarak atar.
    image_path verilirse ve Basic plan varsa görsel eklenir.
    """
    if not config.ENABLE_X:
        logger.info("X paylaşımı kapalı (ENABLE_X=False), atlandı.")
        return False

    if not _configured():
        logger.warning("X (Twitter) ayarlanmamış, atlandı.")
        return False

    try:
        tweet_text = _build_tweet(deal, affiliate_url)
        client = _get_client()

        media_ids = None

        # Görsel yükleme — Basic plan gerekir, hata alırsa görselsiz devam eder
        if image_path and os.path.exists(image_path):
            try:
                api_v1 = _get_v1_api()
                media  = api_v1.media_upload(filename=image_path)
                media_ids = [media.media_id]
                logger.info("X: Görsel yüklendi, media_id=%s", media.media_id)
            except Exception as e:
                logger.warning("X: Görsel yüklenemedi (Basic plan gerekebilir), görselsiz devam: %s", e)
                media_ids = None

        kwargs = {"text": tweet_text}
        if media_ids:
            kwargs["media_ids"] = media_ids

        response = client.create_tweet(**kwargs)
        tweet_id = response.data.get("id") if response.data else "?"
        logger.info("X'e tweet atıldı. Tweet ID: %s", tweet_id)
        return True

    except Exception as e:
        err = str(e)
        if "403" in err:
            logger.error("X 403 hatası — App'in 'Read and Write' izni var mı? developer.x.com kontrol edin.")
        elif "duplicate" in err.lower():
            logger.warning("X: Aynı tweet daha önce atılmış, atlandı.")
        else:
            logger.error("X tweet hatası: %s", e)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_deal = {
        "title":          "QCY H3 Pro ANC Bluetooth 5.4 Kafaüstü Kablosuz Kulaklık Siyah",
        "current_price":  1506,
        "original_price": 2499,
        "discount_pct":   40,
        "asin":           "B0DRSRH3GG",
        "stock_note":     "Stokta sadece 2 adet kaldı.",
    }
    from modules.caption_writer import build_affiliate_url
    url = build_affiliate_url(test_deal["asin"])

    ok = send_tweet(test_deal, url)
    print("Tweet:", "OK" if ok else "Başarısız veya ayarlanmamış")
