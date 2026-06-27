# 🔥 Dip Fiyat — Amazon Fırsat Botu

Amazon'daki indirimli ürünleri otomatik olarak bulup Telegram, Instagram, WhatsApp ve X (Twitter) kanallarınıza paylaşan tam otomatik bot sistemi.

---

## 📌 Özellikler

- **Amazon PA-API v5** ile gerçek zamanlı ürün ve fiyat verisi
- **Keepa API** ile fiyat geçmişi doğrulaması (sahte indirim filtresi)
- Otomatik **görsel oluşturma** (1080x1080 feed + 1080x1920 Reels/Shorts formatı)
- Otomatik **video oluşturma** (60 FPS, animasyonlu, FFmpeg tabanlı)
- Çoklu kanal yayını:
  - 📱 **Telegram** kanalı
  - 📸 **Instagram** (Feed + Reels — Graph API)
  - 💬 **WhatsApp** kanalı
  - 🐦 **X (Twitter)**
- Web tabanlı **dashboard** (Flask)
- **SQLite** veritabanı — aynı ürünü tekrar paylaşmaz
- Windows Task Scheduler uyumlu zamanlayıcı

---

## 🚀 Kurulum

### 1. Depoyu klonlayın
```bash
git clone https://github.com/SuatAyazKun/dip-fiyat.git
cd dip-fiyat
```

### 2. Python bağımlılıklarını kurun
```bash
pip install -r requirements.txt
```

### 3. FFmpeg'i kurun
`setup.bat` dosyasını çalıştırın — FFmpeg'i otomatik indirir ve yapılandırır.
```bash
setup.bat
```

### 4. Ayarları yapılandırın
`.env.example` dosyasını `.env` olarak kopyalayın ve değerleri doldurun:
```bash
cp .env.example .env
```

---

## ⚙️ Yapılandırma (`.env`)

| Değişken | Açıklama |
|---|---|
| `AMAZON_ACCESS_KEY` | Amazon PA-API Access Key |
| `AMAZON_SECRET_KEY` | Amazon PA-API Secret Key |
| `AMAZON_PARTNER_TAG` | Amazon Associates tag |
| `KEEPA_API_KEY` | Keepa API anahtarı |
| `TELEGRAM_BOT_TOKEN` | @BotFather'dan alınan token |
| `TELEGRAM_CHANNEL_ID` | Kanal ID (örn. `-1001234567890`) |
| `INSTAGRAM_USER_ID` | Instagram Business hesap ID |
| `FACEBOOK_PAGE_TOKEN` | Facebook Graph API uzun ömürlü token |
| `GITHUB_TOKEN` | Görsel hosting için GitHub token |
| `WHATSAPP_TOKEN` | Meta Business Cloud API token |
| `X_API_KEY` | X (Twitter) API anahtarı |

Tüm değişkenler için `.env.example` dosyasına bakın.

---

## 📁 Proje Yapısı

```
dip-fiyat/
├── modules/
│   ├── amazon_scraper.py    # Amazon PA-API entegrasyonu
│   ├── deal_finder.py       # Fırsat filtreleme motoru
│   ├── image_creator.py     # Görsel oluşturucu (PIL)
│   ├── video_creator.py     # Instagram Reels video (FFmpeg)
│   ├── shorts_creator.py    # YouTube Shorts video (60 FPS)
│   ├── caption_writer.py    # Otomatik açıklama yazıcı
│   ├── publisher.py         # Çoklu kanal yayıncısı
│   ├── notifier.py          # Admin bildirimleri
│   ├── database.py          # SQLite veritabanı
│   ├── github_pages.py      # Görsel hosting (GitHub)
│   └── x_poster.py          # X (Twitter) entegrasyonu
├── dashboard/
│   ├── app.py               # Flask web arayüzü
│   └── templates/           # HTML şablonları
├── whatsapp_bridge/         # WhatsApp Web.js köprüsü
├── config.py                # Merkezi ayar dosyası (.env'den okur)
├── find_deals_runner.py     # Ana çalıştırıcı
├── scheduler.py             # Zamanlayıcı
├── setup.bat                # Otomatik kurulum scripti
├── .env.example             # Ayar şablonu
└── requirements.txt         # Python bağımlılıkları
```

---

## ▶️ Kullanım

### Fırsat taraması başlat
```bash
python find_deals_runner.py
```

### Dashboard'u aç
```bash
python start_dashboard.pyw
```
Tarayıcıda `http://localhost:5000` adresine gidin.

### Zamanlayıcıyı çalıştır (her gün 08:00, 12:30, 20:00)
```bash
python scheduler.py
```

---

## 🎯 Fırsat Filtreleri

`config.py` içinde özelleştirilebilir:

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `MIN_DISCOUNT_PCT` | `15` | Minimum indirim oranı (%) |
| `MAX_DISCOUNT_PCT` | `75` | Maximum indirim oranı (%) |
| `MIN_SAVING_TRY` | `50` | Minimum tasarruf (TL) |
| `MAX_PRICE_TRY` | `15000` | Maximum ürün fiyatı (TL) |
| `REPOST_DAYS` | `7` | Aynı ürün kaç gün sonra tekrar paylaşılabilir |

---

## 📋 Gereksinimler

- Python 3.10+
- FFmpeg (setup.bat ile otomatik kurulur)
- Amazon Associates hesabı
- Keepa API anahtarı
- Telegram Bot + Kanal
- Instagram Business hesabı + Facebook Graph API erişimi

---

## 📄 Lisans

MIT License — özgürce kullanabilir, değiştirebilir ve dağıtabilirsiniz.
