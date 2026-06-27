"""
Fırsat arama scripti — dashboard tarafından ayrı process olarak çalıştırılır.
"""
import sys
import os
import json
import logging

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
    stream=sys.stdout
)

import config
from modules.deal_finder    import get_top_deals
from modules.amazon_scraper import fetch_product

print("Tarayici baslatiliyor...")
sys.stdout.flush()

candidates = get_top_deals(limit=5)

if not candidates:
    print("Uygun firsat bulunamadi.")
    sys.exit(1)

print(f"{len(candidates)} aday bulundu, detaylar aliniyor...")
sys.stdout.flush()

results = []
for c in candidates:
    deal = fetch_product(c["asin"])
    if deal and deal.get("current_price", 0) > 0:
        deal["image_url"]    = deal.get("image_url") or c.get("image_url", "")
        deal["discount_pct"] = deal.get("discount_pct") or c.get("discount_pct", 0)
        results.append(deal)
        print(f"FIRSAT: {deal['title'][:50]} — {deal['current_price']} TL (%{int(deal['discount_pct'])} indirim)")
        sys.stdout.flush()

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pending_deals.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False)

print(f"Tamamlandi: {len(results)} firsat kaydedildi.")
sys.exit(0)
