"""
Amazon.com.tr Cok Satanlar sayfalarindan ASIN toplar,
her urunun sayfasina girerek gercek indirim tespiti yapar.
"""
import re
import time
import random
import logging
import sys
import os
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from modules.database import is_recently_posted

logger = logging.getLogger(__name__)

BESTSELLER_URLS = [
    'https://www.amazon.com.tr/gp/bestsellers/electronics',
    'https://www.amazon.com.tr/gp/bestsellers/kitchen',
    'https://www.amazon.com.tr/gp/bestsellers/computers',
    'https://www.amazon.com.tr/gp/bestsellers/sporting-goods',
    'https://www.amazon.com.tr/gp/bestsellers/home',
    'https://www.amazon.com.tr/gp/bestsellers/beauty',
    'https://www.amazon.com.tr/gp/bestsellers/toys',
    'https://www.amazon.com.tr/gp/bestsellers/garden',
    'https://www.amazon.com.tr/gp/bestsellers/automotive',
    'https://www.amazon.com.tr/gp/bestsellers/office-products',
    'https://www.amazon.com.tr/gp/bestsellers/pet-supplies',
]

# Anlık fırsat sayfaları (goldbox / new releases)
DEAL_PAGE_URLS = [
    'https://www.amazon.com.tr/gp/goldbox',
    'https://www.amazon.com.tr/gp/new-releases/electronics',
    'https://www.amazon.com.tr/gp/new-releases/kitchen',
    'https://www.amazon.com.tr/gp/new-releases/sports',
]

# Her kategoriden kac ASIN alinsin
ASINS_PER_CATEGORY = 20

# Başlıkta bu kelimelerden biri geçen ürünler atlanır (küçük harf karşılaştırma)
_BLOCKED_KEYWORDS = [
    'külot', 'kulot', 'iç çamaşır', 'ic camasir', 'çorap', 'corap',
    'sütyen', 'sutyen', 'boxer', 'brief', 'thong', 'string',
    'don ', ' don,', 'fanila', 'atlet', 'çorabi', 'corabi',
    'kilot', 'jartiyer', 'tayt', 'külotlu', 'külotlu çorap',
    'bra ', ' bra,', 'panty', 'panties', 'underwear', 'lingerie',
    'sock', 'socks', 'hosiery',
]


def _get_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-software-rasterizer')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--disable-background-networking')
    opts.add_argument('--disable-renderer-backgrounding')
    opts.add_argument('--disable-backgrounding-occluded-windows')
    opts.add_argument('--no-first-run')
    opts.add_argument('--no-default-browser-check')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--lang=tr-TR')
    opts.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    )
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)

    # Chrome binary yolunu açıkça belirt (Server 2016 için)
    for chrome_path in [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]:
        if os.path.exists(chrome_path):
            opts.binary_location = chrome_path
            break

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def _parse_price(text: str) -> float:
    text = text.replace('\xa0', '').replace(' ', '').strip()
    text = re.sub(r'[^\d,]', '', text)
    text = text.replace(',', '.')
    parts = text.split('.')
    if len(parts) > 2:
        text = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(text)
    except Exception:
        return 0.0


def _collect_asins(driver) -> list:
    """Cok satanlar ve firsat sayfalarindan ASIN toplar."""
    all_asins = []
    seen = set()

    for url in BESTSELLER_URLS:
        try:
            driver.get(url)
            time.sleep(1.5)
            soup = BeautifulSoup(driver.page_source, 'lxml')

            cat_count = 0
            for a in soup.select('a.a-link-normal[href*="/dp/"]'):
                m = re.search(r'/dp/([A-Z0-9]{10})', a.get('href', ''))
                if m:
                    asin = m.group(1)
                    if asin not in seen:
                        seen.add(asin)
                        all_asins.append(asin)
                        cat_count += 1
                        if cat_count >= ASINS_PER_CATEGORY:
                            break

            cat = url.split('/')[-1]
            logger.info('Kategori %s: %d ASIN', cat, cat_count)

        except Exception as e:
            logger.error('Kategori hatasi %s: %s', url, e)

    # Firsat sayfalarindan ek ASIN topla (goldbox vb.)
    for url in DEAL_PAGE_URLS:
        try:
            driver.get(url)
            time.sleep(1.0)
            soup = BeautifulSoup(driver.page_source, 'lxml')

            deal_count = 0
            for a in soup.select('a[href*="/dp/"]'):
                m = re.search(r'/dp/([A-Z0-9]{10})', a.get('href', ''))
                if m:
                    asin = m.group(1)
                    if asin not in seen:
                        seen.add(asin)
                        all_asins.insert(0, asin)  # Fırsat sayfası öncelikli
                        deal_count += 1

            cat = url.split('/')[-1]
            logger.info('Firsat sayfasi %s: %d ASIN', cat, deal_count)

        except Exception as e:
            logger.error('Firsat sayfasi hatasi %s: %s', url, e)

    return all_asins


def _check_product_for_deal(driver, asin: str) -> dict | None:
    """
    Urun sayfasina girerek indirim var mi kontrol eder.
    Indirim varsa deal dict dondurur, yoksa None.
    """
    if is_recently_posted(asin):
        return None

    url = f'https://www.amazon.com.tr/dp/{asin}'
    try:
        driver.get(url)
        time.sleep(2.0)
        soup = BeautifulSoup(driver.page_source, 'lxml')

        # Baslik
        title_el = soup.find(id='productTitle')
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        # Yasak kategori filtresi
        title_lower = title.lower()
        if any(kw in title_lower for kw in _BLOCKED_KEYWORDS):
            logger.info('Yasak kategori (giyim/ic camasir), atlaniyor: %s | %s', asin, title[:50])
            return None

        # Guncel fiyat
        current_price = 0.0
        for sel in [
            '#apex-pricetopay-accessibility-label',
            '#corePrice_feature_div .a-offscreen',
            '#corePriceDisplay_desktop_feature_div .a-price .a-offscreen',
            '#apex_desktop_qualifiedBuybox .a-price .a-offscreen',
            '.a-price.aok-align-center .a-offscreen',
            '.reinventPricePriceToPayMargin .a-offscreen',
            '.priceToPay .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '#price_inside_buybox',
            '.apexPriceToPay .a-offscreen',
        ]:
            el = soup.select_one(sel)
            if el:
                v = _parse_price(el.get_text())
                if v > 0:
                    current_price = v
                    break

        if current_price <= 0:
            logger.info('Fiyat alinamadi, atlaniyor: %s', asin)
            return None

        # Amazon'un indirim badge'ini oku
        amazon_discount_pct = 0
        for sel in [
            '[class*=saving]',
            '.savingsPercentage',
            '[class*=savingsPercentage]',
            '#dealprice_savings .a-color-price',
            '.a-size-large.a-color-price',
            '#apex_desktop_qualifiedBuybox [class*=saving]',
            '#corePriceDisplay_desktop_feature_div [class*=saving]',
            '.reinventPriceSavingsPercentageMargin',
        ]:
            el = soup.select_one(sel)
            if el:
                txt = re.sub(r'[^\d]', '', el.get_text())
                if txt and 1 <= int(txt) <= 95:
                    amazon_discount_pct = int(txt)
                    break

        # Eski fiyat
        original_price = 0.0
        for sel in [
            '[data-a-strike="true"] .a-offscreen',
            '.a-price.a-text-price .a-offscreen',
            '.basisPrice .a-offscreen',
            '[class*=basisPrice] .a-offscreen',
            '#corePriceDisplay_desktop_feature_div .a-price.a-text-price .a-offscreen',
            '#apex_desktop_qualifiedBuybox .a-price.a-text-price .a-offscreen',
            '#tmmSwatches .a-price.a-text-price .a-offscreen',
            '.a-text-strike .a-offscreen',
            '[data-a-color="secondary"] .a-offscreen',
            '#listPrice',
            '#priceblock_listprice',
            '.priceBlockStrikePriceString',
        ]:
            el = soup.select_one(sel)
            if el:
                v = _parse_price(el.get_text())
                if current_price < v <= current_price * 4:
                    original_price = v
                    break

        # İndirim tespiti: Amazon badge'i varsa ona güven, yoksa kendi hesapla
        if amazon_discount_pct >= config.MIN_DISCOUNT_PCT and original_price <= current_price:
            # Badge var ama eski fiyat alınamadı — orijinali badge'den hesapla
            original_price = round(current_price / (1 - amazon_discount_pct / 100))

        if original_price <= current_price:
            logger.info('Eski fiyat yok/gecersiz (%.0f -> %.0f), atlaniyor: %s',
                        original_price, current_price, asin)
            return None

        discount_pct = amazon_discount_pct if amazon_discount_pct > 0 else \
            round((original_price - current_price) / original_price * 100)

        # Filtreler
        if discount_pct < config.MIN_DISCOUNT_PCT:
            logger.info('Dusuk indirim %%%d < min %%%d, atlaniyor: %s',
                        discount_pct, config.MIN_DISCOUNT_PCT, asin)
            return None
        if discount_pct > config.MAX_DISCOUNT_PCT:
            logger.info('Cok yuksek indirim %%%d (sahte?), atlaniyor: %s', discount_pct, asin)
            return None
        # original_price güvenilirlik kontrolü: 3 kattan fazlaysa sahte
        if original_price > current_price * 3:
            logger.info('Sahte liste fiyati (%.0f -> %.0f), atlaniyor: %s',
                        original_price, current_price, asin)
            return None
        saving = original_price - current_price
        if saving < config.MIN_SAVING_TRY:
            logger.info('Dusuk tasarruf %.0f TL < min %.0f TL, atlaniyor: %s',
                        saving, config.MIN_SAVING_TRY, asin)
            return None
        if current_price > config.MAX_PRICE_TRY:
            logger.info('Fiyat cok yuksek %.0f TL, atlaniyor: %s', current_price, asin)
            return None

        # Gorsel
        image_url = ''
        img = soup.select_one('#landingImage, #imgBlkFront')
        if img:
            image_url = img.get('data-old-hires') or img.get('src', '')

        # Satici
        seller = ''
        for sel in ['#sellerProfileTriggerId', '#merchant-info a']:
            el = soup.select_one(sel)
            if el:
                seller = el.get_text(strip=True)
                break

        # Stok
        stock_note = ''
        stock_el = soup.select_one('#availability span')
        if stock_el:
            txt = stock_el.get_text(strip=True)
            if txt:
                stock_note = txt

        logger.info('FIRSAT: %s | %.0f TL (-%d%%) | %s',
                    asin, current_price, discount_pct, title[:40])

        return {
            'asin':           asin,
            'title':          title,
            'current_price':  current_price,
            'original_price': original_price,
            'discount_pct':   discount_pct,
            'image_url':      image_url,
            'condition':      'Yeni',
            'stock_note':     stock_note,
            'seller':         seller,
            'category':       'default',
        }

    except Exception as e:
        logger.debug('Urun kontrol hatasi %s: %s', asin, e)
        return None


def get_top_deals(limit: int = 3) -> list:
    """
    Cok satanlar'dan ASIN toplar, her birini kontrol eder,
    en iyi 'limit' adet indirimli urunu dondurur.
    """
    driver = None
    deals = []

    try:
        logger.info('Tarayici baslatiliyor...')
        driver = _get_driver()

        # 1. ASIN topla
        asins = _collect_asins(driver)
        logger.info('Toplam %d ASIN toplandı, indirim kontrolu basliyor...', len(asins))

        # 2. Daha once paylasılmamis ASIN'leri once filtrele
        asins = [a for a in asins if not is_recently_posted(a)]
        logger.info('%d ASIN indirim kontrolune giriyor...', len(asins))

        # 3. Her ASIN'i kontrol et
        for i, asin in enumerate(asins):
            if len(deals) >= limit:
                break
            try:
                logger.info('[ %d / %d ] isleniyor...', i + 1, len(asins))
                deal = _check_product_for_deal(driver, asin)
                if deal:
                    deals.append(deal)
            except Exception:
                logger.warning('Fiyat alinamadi, atlaniyor: %s', asin)

    finally:
        if driver:
            try:
                driver.quit()
                logger.info('Tarayici kapatildi.')
            except Exception:
                pass

    deals.sort(key=lambda x: x['discount_pct'], reverse=True)
    logger.info('Toplam %d firsat bulundu.', len(deals))
    return deals[:limit]


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print('Amazon.com.tr taranıyor (2-3 dakika surebilir)...\n')
    deals = get_top_deals(limit=5)

    if not deals:
        print('Uygun firsat bulunamadi.')
    else:
        print(f'{len(deals)} firsat:\n')
        for i, d in enumerate(deals, 1):
            print(f'{i}. {d["title"][:60]}')
            print(f'   {d["current_price"]} TL  |  %{d["discount_pct"]} indirim')
            print(f'   ASIN: {d["asin"]}')
            print()
