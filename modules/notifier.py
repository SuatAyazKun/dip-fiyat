import requests
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


def send(message: str) -> bool:
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        logger.warning("Telegram ayarlanmamış, bildirim atlandı.")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram bildirimi gönderildi.")
        return True
    except Exception as e:
        logger.error("Telegram hatası: %s", e)
        return False


def send_whatsapp(message: str, to: str = None) -> bool:
    if not config.WHATSAPP_TOKEN or not config.WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp ayarlanmamış, bildirim atlandı.")
        return False

    recipient = to or config.WHATSAPP_CHANNEL_ID
    url = f"https://graph.facebook.com/v25.0/{config.WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": message}
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        logger.info("WhatsApp mesajı gönderildi -> %s", recipient)
        return True
    except Exception as e:
        logger.error("WhatsApp hatası: %s | %s", e, getattr(e, 'response', {}) and e.response.text if hasattr(e, 'response') else '')
        return False


def send_deal_posted(title: str, discount_pct: float, sale_price: float):
    tg_msg = (
        f"✅ <b>Paylaşıldı!</b>\n"
        f"📦 {title}\n"
        f"💰 {sale_price:,.0f} TL  |  %{discount_pct:.0f} indirim"
    )
    wa_msg = (
        f"✅ Paylaşıldı!\n"
        f"📦 {title}\n"
        f"💰 {sale_price:,.0f} TL  |  %{discount_pct:.0f} indirim"
    )
    send(tg_msg)
    send_whatsapp(wa_msg)


def send_no_deals():
    send("ℹ️ Bu turda uygun fırsat bulunamadı.")
    send_whatsapp("ℹ️ Bu turda uygun fırsat bulunamadı.")


def send_error(context: str, error: str):
    tg_msg = f"❌ <b>Hata — {context}</b>\n<code>{error}</code>"
    wa_msg = f"❌ Hata — {context}\n{error}"
    send(tg_msg)
    send_whatsapp(wa_msg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = send("🔔 Dip Fiyat sistemi test mesajı — her şey çalışıyor!")
    if result:
        print("Telegram mesajı başarıyla gönderildi.")
    else:
        print("Telegram ayarlanmamış. config.py dosyasını doldurun.")

    wa_result = send_whatsapp("🔔 Dip Fiyat WhatsApp testi — her şey çalışıyor!")
    if wa_result:
        print("WhatsApp mesajı başarıyla gönderildi.")
    else:
        print("WhatsApp gönderilemedi.")
