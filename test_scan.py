import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1920,1080')
opts.add_argument('--lang=tr-TR')
opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=opts)

# Cok satanlar sayfasindan ASIN topla
BESTSELLER_URLS = [
    'https://www.amazon.com.tr/gp/bestsellers/electronics',
    'https://www.amazon.com.tr/gp/bestsellers/kitchen',
    'https://www.amazon.com.tr/gp/bestsellers/toys',
    'https://www.amazon.com.tr/gp/bestsellers/sports',
    'https://www.amazon.com.tr/gp/bestsellers/computers',
]

all_asins = []
for url in BESTSELLER_URLS:
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    # Cok satanlar sayfasinda ASIN linkleri
    links = soup.select('a.a-link-normal[href*="/dp/"]')
    asins = []
    for a in links:
        href = a.get('href','')
        import re
        m = re.search(r'/dp/([A-Z0-9]{10})', href)
        if m and m.group(1) not in asins:
            asins.append(m.group(1))
    print(f'{url.split("/")[-1]}: {len(asins)} ASIN bulundu')
    all_asins.extend(asins[:10])

print(f'\nToplam ASIN: {len(all_asins)}')
print('Ilk 5:', all_asins[:5])
driver.quit()
