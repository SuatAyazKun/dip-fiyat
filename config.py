# ============================================================
# DIP FIYAT — MERKEZI AYAR DOSYASI
# Tum gizli degerler .env dosyasindan yuklenir.
# Ayarlari degistirmek icin .env dosyasini duzenleyin.
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# --- Amazon Product Advertising API (PA-API v5) ---
AMAZON_ACCESS_KEY  = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY  = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "dipfiyat-21")
AMAZON_REGION      = "eu-west-1"
AMAZON_HOST        = "webservices.amazon.com.tr"

# --- Keepa API ---
KEEPA_API_KEY     = os.getenv("KEEPA_API_KEY", "")
KEEPA_MARKETPLACE = 31

# --- Instagram / Facebook Graph API ---
INSTAGRAM_USER_ID   = os.getenv("INSTAGRAM_USER_ID", "")
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN", "")
GRAPH_API_VERSION   = "v21.0"

# --- Cloudflare R2 ---
R2_ACCOUNT_ID  = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY  = os.getenv("R2_ACCESS_KEY", "")
R2_SECRET_KEY  = os.getenv("R2_SECRET_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "dipfiyat-videos")
R2_PUBLIC_URL  = os.getenv("R2_PUBLIC_URL", "")

# --- Telegram ---
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# --- WhatsApp ---
WHATSAPP_TOKEN      = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID   = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_WABA_ID    = os.getenv("WHATSAPP_WABA_ID", "")
WHATSAPP_CHANNEL_ID = os.getenv("WHATSAPP_CHANNEL_ID", "")
WHATSAPP_KANAL_ID   = os.getenv("WHATSAPP_KANAL_ID", "")

# --- GitHub Pages ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# --- X (Twitter) API v2 ---
ENABLE_X              = os.getenv("ENABLE_X", "False").lower() == "true"
X_API_KEY             = os.getenv("X_API_KEY", "")
X_API_SECRET          = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN        = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")
X_BEARER_TOKEN        = os.getenv("X_BEARER_TOKEN", "")

# --- Firsat Filtreleri ---
MIN_DISCOUNT_PCT = 15
MAX_DISCOUNT_PCT = 75
MIN_SAVING_TRY   = 50
MAX_PRICE_TRY    = 15000
MIN_RATING       = 0.0
MIN_REVIEWS      = 0
REPOST_DAYS      = 7

# --- Video Ayarlari ---
VIDEO_WIDTH    = 1080
VIDEO_HEIGHT   = 1920
VIDEO_DURATION = 30
VIDEO_FPS      = 30

# Renkler (RGB)
BG_COLOR     = (15, 15, 25)
ACCENT_COLOR = (220, 40, 40)
PRICE_COLOR  = (40, 210, 90)
TEXT_COLOR   = (255, 255, 255)
BADGE_BG     = (220, 40, 40)

# --- Gunluk Paylasim Saatleri ---
POST_TIMES = ["08:00", "12:30", "20:00"]

# --- Yollar ---
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR      = os.path.join(BASE_DIR, "assets")
FONT_PATH       = r"C:\Windows\Fonts\arialbd.ttf"
FONT_LIGHT_PATH = r"C:\Windows\Fonts\arial.ttf"
MUSIC_PATH      = os.path.join(ASSETS_DIR, "music", "upbeat_free.mp3")
TEMPLATE_PATH   = os.path.join(ASSETS_DIR, "templates", "template_bg.png")
TEMP_DIR        = os.path.join(ASSETS_DIR, "temp")
OUTPUT_DIR      = os.path.join(BASE_DIR, "output", "videos")
LOG_PATH        = os.path.join(BASE_DIR, "logs", "app.log")
DB_PATH         = os.path.join(BASE_DIR, "data", "deals.db")
FFMPEG_PATH     = os.path.join(BASE_DIR, "ffmpeg.exe")
