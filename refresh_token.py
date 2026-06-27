"""
Facebook Page Token'i otomatik yeniler.
Her 50 günde bir Görev Zamanlayıcı tarafından çalıştırılır.

Yöntem:
  1. Mevcut token ile /oauth/access_token?grant_type=fb_exchange_token çağrısı yapılır.
     Bu, kısa ömürlü token'ı 60 günlük uzun ömürlü token'a dönüştürür.
  2. Yeni token config.py'ye yazılır.

NOT: Bu yöntem token expire olmadan önce çalıştırılmalıdır (her 50 günde bir).
Token zaten expire olduysa manuel yenileme gerekir.
"""
import requests
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

APP_ID     = "975592645251342"
APP_SECRET = "4c7a2b7c5088ca0d979fe01f2b290709"


def extend_token(current_token: str) -> str:
    """Kısa/süresi yaklaşan token'ı 60 günlük uzun ömürlü token'a çevirir."""
    r = requests.get(
        "https://graph.facebook.com/v21.0/oauth/access_token",
        params={
            "grant_type":        "fb_exchange_token",
            "client_id":         APP_ID,
            "client_secret":     APP_SECRET,
            "fb_exchange_token": current_token,
        },
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    return data["access_token"]


def get_page_token(user_token: str) -> str:
    """User token ile sayfa token'ını alır (sayfa token'ı süresi dolmaz)."""
    r = requests.get(
        "https://graph.facebook.com/v21.0/me/accounts",
        params={"access_token": user_token},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    pages = data.get("data", [])
    if not pages:
        raise RuntimeError("Hesaba bağlı Facebook sayfası bulunamadı.")
    return pages[0]["access_token"]


def write_token_to_config(new_token: str):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    old_token = config.FACEBOOK_PAGE_TOKEN
    if old_token not in content:
        raise RuntimeError("Eski token config.py'de bulunamadı, manuel güncelleme gerekiyor.")
    content = content.replace(old_token, new_token)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)


def refresh_page_token():
    from modules.publisher import notify_admin
    try:
        logger.info("Token yenileme başlatıldı...")

        # Adım 1: Mevcut token'ı uzat (User long-lived token al)
        long_lived = extend_token(config.FACEBOOK_PAGE_TOKEN)
        logger.info("Uzun ömürlü user token alındı.")

        # Adım 2: Page token al (süresi dolmaz)
        page_token = get_page_token(long_lived)
        logger.info("Page token alındı.")

        # Adım 3: config.py'ye yaz
        write_token_to_config(page_token)
        logger.info("Token başarıyla yenilendi ve config.py güncellendi.")

        notify_admin("✅ Instagram token otomatik yenilendi (60 gün uzatıldı).")
        return True

    except Exception as e:
        logger.error("Token yenileme hatası: %s", e)
        try:
            from modules.publisher import notify_admin
            notify_admin(
                f"⚠️ Instagram token yenilenemedi!\n"
                f"Hata: {e}\n\n"
                f"Manuel yenileme:\n"
                f"developers.facebook.com → Graph API Explorer → Generate Access Token"
            )
        except Exception:
            pass
        return False


if __name__ == "__main__":
    ok = refresh_page_token()
    if ok:
        print("Token başarıyla yenilendi.")
    else:
        print("Token yenilenemedi — manuel yenileme gerekiyor.")
    sys.exit(0 if ok else 1)
