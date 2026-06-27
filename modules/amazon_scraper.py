"""
Amazon.com.tr ürün sayfasından bilgi çeker.
Girdi: Amazon ürün URL'si veya ASIN
Çıktı: deal dict (image_creator ve caption_writer'ın beklediği format)
"""
import re
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def extract_asin(url: str) -> str:
    if re.match(r"^[A-Z0-9]{10}$", url.strip()):
        return url.strip()
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    if match:
        return match.group(1)
    match = re.search(r"/gp/product/([A-Z0-9]{10})", url)
    if match:
        return match.group(1)
    raise ValueError(f"ASIN bulunamadı: {url}")


def _parse_price(text: str) -> float:
    text = text.replace("TL", "").replace("\xa0", "").strip()
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return 0.0


def _get_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=tr-TR")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def _scrape_with_selenium(asin: str) -> dict | None:
    driver = None
    try:
        from bs4 import BeautifulSoup
        driver = _get_driver()
        url = f"https://www.amazon.com.tr/dp/{asin}"
        driver.get(url)
        time.sleep(2.5)
        soup = BeautifulSoup(driver.page_source, "lxml")
        return _parse_soup(asin, soup)
    except Exception as e:
        logger.error("Selenium scrape hatasi [%s]: %s", asin, e)
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _parse_soup(asin: str, soup) -> dict | None:
    from bs4 import BeautifulSoup

    # Başlık
    title = ""
    title_tag = soup.find(id="productTitle")
    if title_tag:
        title = title_tag.get_text(strip=True)
    if not title:
        return None

    # Güncel fiyat
    current_price = 0.0
    for selector in [
        "#apex-pricetopay-accessibility-label",
        "#corePrice_feature_div .a-offscreen",
        ".a-price.aok-align-center .a-offscreen",
        ".priceToPay .a-offscreen",
        "#priceblock_dealprice",
        "#priceblock_ourprice",
    ]:
        el = soup.select_one(selector)
        if el:
            v = _parse_price(el.get_text())
            if v > 0:
                current_price = v
                break

    # Eski fiyat
    original_price = 0.0
    for selector in [
        '[data-a-strike="true"] .a-offscreen',
        ".a-price.a-text-price .a-offscreen",
        ".basisPrice .a-offscreen",
        '[class*=basisPrice] .a-offscreen',
    ]:
        el = soup.select_one(selector)
        if el:
            v = _parse_price(el.get_text())
            if current_price > 0 and current_price < v <= current_price * 4:
                original_price = v
                break

    if original_price <= current_price:
        original_price = 0.0

    # İndirim yüzdesi — Amazon'un kendi badge'ini önce dene
    discount_pct = 0.0
    for badge_sel in ['[class*=saving]', '.savingsPercentage', '[class*=savingsPercentage]']:
        badge = soup.select_one(badge_sel)
        if badge:
            m = re.search(r'(\d+)', badge.get_text())
            if m and int(m.group(1)) <= 90:
                discount_pct = float(m.group(1))
                break
    if not discount_pct and original_price > 0 and current_price > 0:
        discount_pct = round((original_price - current_price) / original_price * 100)

    # Ürün görseli
    image_url = ""
    img_tag = soup.select_one("#landingImage, #imgBlkFront, #main-image")
    if img_tag:
        image_url = img_tag.get("data-old-hires") or img_tag.get("src", "")
        if not image_url and img_tag.get("data-a-dynamic-image"):
            try:
                image_url = list(__import__("json").loads(img_tag["data-a-dynamic-image"]).keys())[0]
            except Exception:
                pass

    # Durum
    condition = "Yeni"
    condition_tag = soup.select_one("#renewedBadge-title, #usedBuySection .a-color-secondary")
    if condition_tag:
        condition = condition_tag.get_text(strip=True)

    # Stok notu
    stock_note = ""
    stock_tag = soup.select_one("#availability span")
    if stock_tag:
        txt = stock_tag.get_text(strip=True)
        if txt:
            stock_note = txt

    # Satıcı
    seller = ""
    for sel in ["#sellerProfileTriggerId", "#merchant-info a"]:
        el = soup.select_one(sel)
        if el:
            seller = el.get_text(strip=True)
            break

    logger.info("Urun cekildi: %s — %.2f TL", title[:50], current_price)

    return {
        "asin":           asin,
        "title":          title,
        "current_price":  current_price,
        "original_price": original_price,
        "discount_pct":   discount_pct,
        "image_url":      image_url,
        "condition":      condition,
        "stock_note":     stock_note,
        "seller":         seller,
        "category":       "default",
    }


def fetch_product(url_or_asin: str) -> dict | None:
    try:
        asin = extract_asin(url_or_asin)
    except ValueError as e:
        logger.error("%s", e)
        return None

    return _scrape_with_selenium(asin)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    test_url = "https://www.amazon.com.tr/dp/B0DRSRH3GG"
    result = fetch_product(test_url)
    if result:
        for k, v in result.items():
            print(f"{k:20}: {v}")
    else:
        print("Urun bilgisi alinamadi.")
