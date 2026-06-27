"""
pending_deals.json'daki ilk N ürünü Instagram'a gönderir.
Kullanım:
    python post_to_instagram.py          # ilk 3 ürünü gönderir
    python post_to_instagram.py 5        # ilk 5 ürünü gönderir
"""
import sys
import os
import json
import logging

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
    stream=sys.stdout,
)

import config
from modules.image_creator  import create_image, create_instagram_image
from modules.caption_writer import generate, build_affiliate_url
from modules.publisher      import send_to_instagram
from modules.github_pages   import upload_image, update_page, get_recent_deals_for_page
from modules.database       import init_db, is_recently_posted, mark_posted

PENDING_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pending_deals.json")

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def main():
    init_db()

    if not os.path.exists(PENDING_PATH):
        print("pending_deals.json bulunamadi. Once 'Firsatlari Bul' calistirin.")
        sys.exit(1)

    with open(PENDING_PATH, "r", encoding="utf-8") as f:
        deals = json.load(f)

    if not deals:
        print("Gonderilecek firsat yok.")
        sys.exit(0)

    candidates = deals[:limit]
    print(f"{len(candidates)} firsat Instagram'a gonderilecek.\n")

    posted_count = 0
    for deal in candidates:
        asin  = deal.get("asin", "")
        title = deal.get("title", "")[:60]
        print(f"--- {asin}: {title}")

        if is_recently_posted(asin):
            print(f"  Atlandi: son {config.REPOST_DAYS} gun icinde paylasıldi.")
            continue

        # Instagram kare görseli oluştur
        ig_local = create_instagram_image(deal)
        if not ig_local:
            ig_local = create_image(deal)

        if not ig_local or not os.path.exists(ig_local):
            print("  Gorsel olusturulamadi, atlaniyor.")
            continue

        # GitHub'a yükle (public URL gerekli)
        public_url = upload_image(ig_local)
        if not public_url:
            print("  GitHub yukleme basarisiz, atlaniyor.")
            continue

        affiliate_url = build_affiliate_url(asin)
        caption       = generate(deal, affiliate_url)

        ok = send_to_instagram(public_url, caption)
        if ok:
            mark_posted(
                asin, deal["title"],
                deal.get("discount_pct", 0),
                deal.get("original_price", 0),
                deal.get("current_price", 0),
                ig_local,
                image_url=deal.get("image_url", ""),
            )
            posted_count += 1
            print(f"  Gonderildi! ({deal.get('current_price', 0):.0f} TL  %{int(deal.get('discount_pct', 0))} indirim)")
        else:
            print("  Instagram gonderilemedi.")

    print(f"\nTamamlandi: {posted_count}/{len(candidates)} gonderi paylasıldı.")

    if posted_count > 0:
        update_page(get_recent_deals_for_page(limit=50))
        print("GitHub Pages guncellendi.")


if __name__ == "__main__":
    main()
