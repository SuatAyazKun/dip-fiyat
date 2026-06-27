"""
Her paylasimdan sonra GitHub Pages link sayfasini otomatik gunceller.
Sayfa: https://sazy67.github.io/dipfiyat-links
"""
import json
import base64
import logging
import requests
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

GITHUB_TOKEN    = config.GITHUB_TOKEN
GITHUB_USER     = "Sazy67"
GITHUB_REPO     = "dipfiyat-links"
GITHUB_BRANCH   = "main"
FILE_PATH       = "index.html"
API_BASE        = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{FILE_PATH}"
IMAGES_API_BASE = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/images"


def upload_image(local_path: str) -> str:
    """Görseli GitHub repo'ya yükler, public URL döndürür."""
    if not GITHUB_TOKEN or GITHUB_TOKEN == "YOUR_GITHUB_TOKEN":
        return ""
    try:
        filename = os.path.basename(local_path)
        api_url  = f"{IMAGES_API_BASE}/{filename}"
        headers  = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        # Mevcut dosya varsa SHA al (update için gerekli)
        sha = ""
        r = requests.get(api_url, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha", "")

        payload = {
            "message": f"Gorsel eklendi: {filename}",
            "content": content,
            "branch":  GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(api_url, json=payload, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            public_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/images/{filename}"
            logger.info("Gorsel GitHub'a yuklendi: %s", public_url)
            return public_url
        else:
            logger.error("GitHub gorsel yukleme hatasi: %s", r.text[:200])
            return ""
    except Exception as e:
        logger.error("GitHub gorsel yukleme exception: %s", e)
        return ""


def _get_current_sha() -> str:
    """Mevcut dosyanin SHA'sini alir (guncelleme icin gerekli)."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(API_BASE, headers=headers, timeout=10)
    if resp.status_code == 200:
        return resp.json().get("sha", "")
    return ""


_SOCIAL = {
    "telegram":  ("https://t.me/Dip_Fiyat",                          "@dipfiyatt · Anlık bildirimler"),
    "instagram": ("https://www.instagram.com/dip.fiyat",             "@dip.fiyat · Görsel fırsatlar"),
    "whatsapp":  ("https://whatsapp.com/channel/0029Vb8GwyK59PwPOtb3j13W", "Dip.Fiyat · Anlık fırsatlar"),
}
_TG  = _SOCIAL["telegram"][0]
_IG  = _SOCIAL["instagram"][0]
_WA  = _SOCIAL["whatsapp"][0]


def _build_html(deals: list) -> str:
    """Link sayfasi HTML'ini olusturur."""
    items_html = ""
    for d in deals:
        pct = int(d["discount_pct"]) if d.get("discount_pct") else 0
        discount_badge = f'<span class="badge">%{pct} İndirim</span>' if pct else ""
        old_price = (f'<span class="old-price">{d["original_price"]:,.0f} TL</span>'.replace(",", ".")
                     if d.get("original_price") else "")
        savings = ""
        if d.get("original_price") and d.get("current_price"):
            saved = d["original_price"] - d["current_price"]
            if saved > 0:
                savings = f'<span class="savings">▼ {saved:,.0f} TL tasarruf</span>'.replace(",", ".")
        safe_title = d['title'][:50].replace("'", "\\'")
        items_html += f"""
        <a href="{d['affiliate_url']}" class="deal-card" target="_blank" rel="noopener"
           onclick="trackClick('{d['asin']}', '{safe_title}', {d['current_price']})">
          <div class="deal-img">
            <img src="{d.get('image_url','')}" alt="{d['title']}" loading="lazy" onerror="this.style.display='none'">
          </div>
          <div class="deal-info">
            <div class="deal-title">{d['title'][:75]}</div>
            <div class="deal-price">
              {old_price}
              <span class="new-price">{d['current_price']:,.0f} TL</span>
              {discount_badge}
            </div>
            {savings}
          </div>
          <div class="deal-cta">Fırsata Git →</div>
        </a>
        """.replace(",", ".")

    updated = datetime.now().strftime("%d.%m.%Y %H:%M")
    deal_count = len(deals)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dip Fiyat — Amazon'un En İyi Fırsatları</title>
<meta name="description" content="Amazon'da gerçek dip fiyatları yakalıyoruz. Günlük %30-60 indirimli ürünler Telegram ve Instagram kanallarımızda!">
<meta property="og:title" content="Dip Fiyat — Amazon Fırsatları">
<meta property="og:description" content="Amazon'un gerçek dip fiyatlarını sizinle paylaşıyoruz. Ücretsiz abone olun, fırsatları kaçırmayın!">
<meta property="og:image" content="https://raw.githubusercontent.com/Sazy67/dipfiyat-links/main/images/og_preview.png">
<meta name="theme-color" content="#ff4b00">
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-N8K3X0HN7C"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-N8K3X0HN7C');
  function trackClick(asin, title, price){{
    gtag('event', 'urun_tikla', {{
      'event_category': 'Urun',
      'event_label': asin,
      'value': Math.round(price),
      'urun_adi': title.substring(0, 50)
    }});
  }}
  function trackChannel(name){{
    gtag('event', 'kanal_tikla', {{
      'event_category': 'Kanal',
      'event_label': name
    }});
  }}
</script>
<style>
:root {{
  --brand: #ff4b00;
  --brand2: #ff8c00;
  --green: #00b341;
  --dark: #0f0f1a;
  --card-bg: #fff;
  --page-bg: #f2f3f7;
  --text: #1a1a1a;
  --muted: #888;
  --radius: 16px;
}}
*,*::before,*::after{{ box-sizing:border-box; margin:0; padding:0; }}
body{{
  font-family:'Segoe UI',system-ui,-apple-system,sans-serif;
  background:var(--page-bg);
  color:var(--text);
  min-height:100vh;
}}

/* ── HERO ── */
.hero{{
  background:linear-gradient(135deg,#0f0f1a 0%,#1a0a00 60%,#2d0d00 100%);
  padding:40px 16px 32px;
  text-align:center;
  position:relative;
  overflow:hidden;
}}
.hero::before{{
  content:'';
  position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 0%,rgba(255,75,0,.25) 0%,transparent 70%);
  pointer-events:none;
}}
.hero-logo{{
  font-size:2.6rem;
  font-weight:900;
  letter-spacing:-1px;
  color:#fff;
  line-height:1;
}}
.hero-logo span{{ color:var(--brand); }}
.hero-tagline{{
  font-size:.95rem;
  color:rgba(255,255,255,.7);
  margin:8px 0 24px;
}}
.hero-stats{{
  display:flex;
  justify-content:center;
  gap:24px;
  margin-bottom:28px;
}}
.stat{{
  text-align:center;
}}
.stat-num{{
  font-size:1.5rem;
  font-weight:800;
  color:var(--brand);
}}
.stat-label{{
  font-size:.7rem;
  color:rgba(255,255,255,.55);
  text-transform:uppercase;
  letter-spacing:.5px;
}}

/* ── KANAL BUTONLARI ── */
.channels{{
  display:flex;
  flex-direction:row;
  gap:12px;
  max-width:860px;
  margin:0 auto;
  justify-content:center;
}}
.chan-btn{{
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:10px;
  padding:18px 16px 14px;
  border-radius:14px;
  text-decoration:none;
  font-weight:700;
  font-size:.95rem;
  transition:transform .15s,filter .15s;
  flex:1;
  text-align:center;
}}
.chan-btn::after{{
  content:'Abone Ol →';
  font-size:.75rem;
  font-weight:600;
  opacity:.85;
  margin-top:2px;
}}
.chan-btn:hover{{ transform:translateY(-2px); filter:brightness(1.08); }}
.chan-btn svg{{ flex-shrink:0; }}

.btn-telegram{{
  background:linear-gradient(135deg,#229ed9,#1a7fad);
  color:#fff;
}}
.btn-instagram{{
  background:linear-gradient(135deg,#f58529,#dd2a7b 45%,#8134af);
  color:#fff;
}}
.btn-whatsapp{{
  background:linear-gradient(135deg,#25d366,#128c7e);
  color:#fff;
}}
.chan-info{{ display:flex; flex-direction:column; gap:2px; align-items:center; }}
.chan-name{{ font-size:1rem; font-weight:800; }}
.chan-sub{{ font-size:.75rem; opacity:.8; font-weight:400; }}

/* ── BÖLÜM BAŞLIĞI ── */
.section-header{{
  max-width:900px;
  margin:32px auto 0;
  padding:0 16px;
  display:flex;
  align-items:center;
  justify-content:space-between;
}}
.section-title{{
  font-size:1.1rem;
  font-weight:800;
  color:var(--dark);
}}
.live-dot{{
  display:flex;
  align-items:center;
  gap:6px;
  font-size:.75rem;
  color:var(--muted);
}}
.live-dot::before{{
  content:'';
  width:8px;height:8px;
  border-radius:50%;
  background:var(--green);
  animation:pulse 1.8s ease infinite;
}}
@keyframes pulse{{
  0%,100%{{opacity:1;transform:scale(1)}}
  50%{{opacity:.5;transform:scale(1.3)}}
}}

/* ── DEAL CARDS ── */
.container{{
  max-width:900px;
  margin:12px auto 0;
  padding:0 16px 24px;
}}
.deals-grid{{
  display:grid;
  grid-template-columns:repeat(2,1fr);
  gap:12px;
}}
.deal-card{{
  display:flex;
  flex-direction:column;
  background:var(--card-bg);
  border-radius:var(--radius);
  padding:14px;
  box-shadow:0 2px 12px rgba(0,0,0,.07);
  text-decoration:none;
  color:inherit;
  gap:10px;
  transition:transform .15s,box-shadow .15s;
  border:1.5px solid transparent;
}}
.deal-card:hover{{
  transform:translateY(-2px);
  box-shadow:0 6px 24px rgba(255,75,0,.13);
  border-color:rgba(255,75,0,.2);
}}
.deal-img{{
  width:100%;height:120px;
  border-radius:10px;
  overflow:hidden;
  background:#f7f7f7;
  display:flex;align-items:center;justify-content:center;
}}
.deal-img img{{ width:100%;height:100%;object-fit:contain; }}
.deal-info{{ flex:1;min-width:0; }}
.deal-title{{
  font-size:.85rem;
  font-weight:600;
  color:#222;
  margin-bottom:7px;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
  line-height:1.35;
}}
.deal-price{{ display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:4px; }}
.old-price{{ font-size:.78rem;color:#bbb;text-decoration:line-through; }}
.new-price{{ font-size:1.1rem;font-weight:800;color:var(--green); }}
.badge{{
  background:var(--brand);color:#fff;
  font-size:.68rem;font-weight:700;
  padding:2px 8px;border-radius:20px;
}}
.savings{{ font-size:.72rem;color:var(--muted); }}
.deal-cta{{
  background:var(--brand);
  color:#fff;
  font-size:.76rem;
  font-weight:700;
  padding:9px 13px;
  border-radius:10px;
  text-align:center;
  line-height:1.3;
  margin-top:auto;
}}

/* ── BANNER ── */
.promo-banner{{
  max-width:900px;
  margin:20px auto 0;
  padding:0 16px;
}}
.promo-inner{{
  background:linear-gradient(135deg,var(--dark),#1a0a00);
  border-radius:var(--radius);
  padding:22px 20px;
  text-align:center;
  border:1px solid rgba(255,75,0,.25);
}}
.promo-inner h3{{
  color:#fff;
  font-size:1.05rem;
  margin-bottom:8px;
}}
.promo-inner p{{
  color:rgba(255,255,255,.6);
  font-size:.83rem;
  margin-bottom:16px;
  line-height:1.5;
}}
.promo-btns{{
  display:flex;gap:10px;justify-content:center;flex-wrap:wrap;
}}
.promo-btn{{
  padding:10px 20px;
  border-radius:10px;
  font-weight:700;
  font-size:.85rem;
  text-decoration:none;
  transition:transform .15s;
}}
.promo-btn:hover{{transform:translateY(-2px);}}
.promo-btn-tg{{ background:#229ed9;color:#fff; }}
.promo-btn-ig{{ background:linear-gradient(135deg,#f58529,#dd2a7b);color:#fff; }}
.promo-btn-wa{{ background:#25d366;color:#fff; }}

/* ── FOOTER ── */
footer{{
  text-align:center;
  padding:28px 16px;
  font-size:.75rem;
  color:#bbb;
  line-height:1.8;
}}
footer a{{ color:var(--brand);text-decoration:none; }}

.empty{{
  text-align:center;padding:60px 20px;
  color:#bbb;font-size:1rem;
}}

/* ── MOBİL ── */
@media(max-width:600px){{
  .hero-logo{{font-size:2.1rem;}}
  .deal-cta{{display:block;}}
  .deal-title{{font-size:.84rem;}}
  .deals-grid{{grid-template-columns:1fr;}}
  .channels{{flex-direction:column;max-width:400px;}}
}}
</style>
</head>
<body>

<!-- HERO -->
<div class="hero">
  <div class="hero-logo">🔥 DİP<span>FİYAT</span></div>
  <p class="hero-tagline">Amazon'un gerçek dip fiyatlarını sizinle paylaşıyoruz</p>

  <div class="hero-stats">
    <div class="stat">
      <div class="stat-num">{deal_count}+</div>
      <div class="stat-label">Aktif Fırsat</div>
    </div>
    <div class="stat">
      <div class="stat-num">%30+</div>
      <div class="stat-label">Min. İndirim</div>
    </div>
    <div class="stat">
      <div class="stat-num">Günlük</div>
      <div class="stat-label">Güncelleme</div>
    </div>
  </div>

  <div class="channels">
    <!-- Telegram -->
    <a href="{_TG}" class="chan-btn btn-telegram" target="_blank" rel="noopener" onclick="trackChannel('telegram')">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="white"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248-2.02 9.52c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.883.701z"/></svg>
      <div class="chan-info">
        <span class="chan-name">Telegram Kanalı</span>
        <span class="chan-sub">@dipfiyatt · Anlık bildirimler</span>
      </div>
    </a>
    <!-- Instagram -->
    <a href="{_IG}" class="chan-btn btn-instagram" target="_blank" rel="noopener" onclick="trackChannel('instagram')">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="white"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
      <div class="chan-info">
        <span class="chan-name">Instagram</span>
        <span class="chan-sub">@dip.fiyat · Görsel fırsatlar</span>
      </div>
    </a>
    <!-- WhatsApp -->
    <a href="{_WA}" class="chan-btn btn-whatsapp" target="_blank" rel="noopener" onclick="trackChannel('whatsapp')">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="white"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
      <div class="chan-info">
        <span class="chan-name">WhatsApp Kanalı</span>
        <span class="chan-sub">Dip.Fiyat · Anlık fırsatlar</span>
      </div>
    </a>
  </div>
</div>

<!-- PROMO BANNER -->
<div class="promo-banner">
  <div class="promo-inner">
    <h3>💸 Fırsatları Kaçırma!</h3>
    <p>Her gün sabah 08:00, öğle 12:30 ve akşam 20:00'da<br>en güncel Amazon dip fiyatlarını kanallarımıza gönderiyoruz.</p>
    <div class="promo-btns">
      <a href="{_TG}" class="promo-btn promo-btn-tg" target="_blank" rel="noopener">Telegram'a Katıl</a>
      <a href="{_IG}" class="promo-btn promo-btn-ig" target="_blank" rel="noopener">Instagram</a>
      <a href="{_WA}" class="promo-btn promo-btn-wa" target="_blank" rel="noopener">WhatsApp Kanalı</a>
    </div>
  </div>
</div>

<!-- DEAL LİSTESİ -->
<div class="section-header">
  <span class="section-title">Son Fırsatlar</span>
  <span class="live-dot">Son güncelleme: {updated}</span>
</div>

<div class="container">
  {'<div class="empty">Henüz fırsat yok, yakında!</div>' if not deals else '<div class="deals-grid">' + items_html + '</div>'}
</div>

<!-- ALT BANNER -->
<div class="promo-banner">
  <div class="promo-inner">
    <h3>📢 Arkadaşını Bilgilendir</h3>
    <p>Bu sayfayı arkadaşlarınla paylaş, birlikte daha çok tasarruf edin.<br>Tamamen ücretsiz, reklam yok, sadece gerçek fırsatlar.</p>
    <div class="promo-btns">
      <a href="{_TG}" class="promo-btn promo-btn-tg" target="_blank" rel="noopener">Telegram Kanalı</a>
      <a href="{_IG}" class="promo-btn promo-btn-ig" target="_blank" rel="noopener">Instagram</a>
      <a href="{_WA}" class="promo-btn promo-btn-wa" target="_blank" rel="noopener">WhatsApp Kanalı</a>
    </div>
  </div>
</div>

<footer>
  <p>🔥 <strong>Dip Fiyat</strong> — Amazon Türkiye'nin en iyi fırsatları</p>
  <p style="margin-top:6px">
    <a href="{_TG}">Telegram</a> &nbsp;·&nbsp;
    <a href="{_IG}">Instagram</a> &nbsp;·&nbsp;
    <a href="{_WA}">WhatsApp</a>
  </p>
  <p style="margin-top:10px;font-size:.68rem">
    Bu sayfa affiliate linkler içermektedir. Amazon ortağı olarak uygun satın alımlardan komisyon kazanılmaktadır.
  </p>
</footer>

</body>
</html>"""


def update_page(deals: list) -> bool:
    """GitHub Pages sayfasini gunceller."""
    if not GITHUB_TOKEN or GITHUB_TOKEN == "YOUR_GITHUB_TOKEN":
        logger.warning("GitHub token ayarlanmamis, atlandi.")
        return False

    try:
        html    = _build_html(deals)
        content = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        sha     = _get_current_sha()

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {
            "message": f"Firsat guncellendi — {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "content": content,
            "branch":  GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        resp = requests.put(API_BASE, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201):
            logger.info("GitHub Pages guncellendi: https://%s.github.io/%s", GITHUB_USER.lower(), GITHUB_REPO)
            return True
        else:
            logger.error("GitHub Pages hatasi: %s — %s", resp.status_code, resp.text[:200])
            return False

    except Exception as e:
        logger.error("GitHub Pages exception: %s", e)
        return False


def get_recent_deals_for_page(limit: int = 50) -> list:
    """Veritabanindan son firsatlari ceker, link sayfasi icin hazirlar."""
    import sqlite3
    from modules.caption_writer import build_affiliate_url

    try:
        conn = sqlite3.connect(config.DB_PATH)
        rows = conn.execute(
            """SELECT asin, title, discount_pct, original_price, sale_price,
                      COALESCE(image_url, '') as image_url
               FROM posted_deals ORDER BY posted_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
    except Exception:
        return []

    deals = []
    for row in rows:
        asin, title, discount_pct, orig, sale, image_url = row

        # Veritabanında URL yoksa fallback
        if not image_url:
            image_url = f"https://m.media-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_.jpg"

        deals.append({
            "asin":          asin,
            "title":         title,
            "current_price": sale or 0,
            "original_price":orig or 0,
            "discount_pct":  discount_pct or 0,
            "image_url":     image_url,
            "affiliate_url": build_affiliate_url(asin),
        })
    return deals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    deals = get_recent_deals_for_page()
    print(f"{len(deals)} firsat bulundu, sayfa guncelleniyor...")
    ok = update_page(deals)
    print("Sonuc:", "Basarili!" if ok else "Basarisiz!")
    if ok:
        print(f"Sayfa: https://{GITHUB_USER.lower()}.github.io/{GITHUB_REPO}")
