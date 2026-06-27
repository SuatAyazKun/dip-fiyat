"""
Instagram paylaşımı için Türkçe caption ve hashtag üretir.
Affiliate linki caption'ın içine gömülür.
"""
import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

CATEGORY_HASHTAGS = {
    "Electronics":       ["#teknoloji", "#elektronik", "#telefon", "#kulaklık", "#bilgisayar"],
    "Computers":         ["#bilgisayar", "#laptop", "#teknoloji", "#gaming"],
    "Kitchen":           ["#mutfak", "#ev", "#yaşam", "#yemek"],
    "Sports":            ["#spor", "#fitness", "#sağlık", "#antrenman"],
    "Books":             ["#kitap", "#okuma", "#eğitim", "#kişiselgelişim"],
    "Fashion":           ["#moda", "#giyim", "#stil", "#trend"],
    "Home":              ["#ev", "#dekorasyon", "#yaşam", "#tasarım"],
    "Toys":              ["#oyuncak", "#çocuk", "#eğlence"],
    "Beauty":            ["#güzellik", "#ciltbakımı", "#makyaj"],
    "default":           ["#ucuz", "#alışveriş", "#trend", "#teklif"],
}

BASE_HASHTAGS = "#dipfiyat #amazon #amazontürkiye #indirim #kampanya #fırsat"

SITE_FOOTER = "🌐 Tüm fırsatlar için → dipfiyatci.com"


def build_affiliate_url(asin: str) -> str:
    link_id = uuid.uuid4().hex[:16]
    return (
        f"https://www.amazon.com.tr/dp/{asin}"
        f"?linkCode=ll2"
        f"&tag={config.AMAZON_PARTNER_TAG}"
        f"&linkId={link_id}"
        f"&ref_=as_li_ss_tl"
    )


def shorten_url(long_url: str) -> str:
    """TinyURL ile linki kisaltir."""
    try:
        import requests
        resp = requests.get(
            f"https://tinyurl.com/api-create.php?url={long_url}",
            timeout=5
        )
        if resp.status_code == 200 and resp.text.startswith("http"):
            return resp.text.strip()
    except Exception:
        pass
    return long_url


def generate(deal: dict, affiliate_url: str = "", plain_link: bool = False) -> str:
    """
    Telegram caption metni üretir.
    deal dict anahtarları:
        title, current_price, original_price, discount_pct,
        asin, category, stock_note, seller, condition
    """
    title          = deal.get("title", "")
    current_price  = deal.get("current_price", 0)
    original_price = deal.get("original_price", 0)
    discount_pct   = deal.get("discount_pct", 0)
    category       = deal.get("category", "default")
    stock_note     = deal.get("stock_note", "")
    seller         = deal.get("seller", "")
    condition      = deal.get("condition", "")

    if not affiliate_url and deal.get("asin"):
        affiliate_url = build_affiliate_url(deal["asin"])

    cat_tags = CATEGORY_HASHTAGS.get(category, CATEGORY_HASHTAGS["default"])
    all_tags = BASE_HASHTAGS + "  " + "  ".join(cat_tags)

    lines = []
    lines.append(f"🔥 {title}")
    lines.append("")

    if original_price and original_price > current_price:
        lines.append(f"❌ Normal Fiyat: {original_price:,.0f} TL".replace(",", "."))

    lines.append(f"💰 {current_price:,.0f} TL".replace(",", "."))

    if discount_pct >= 1:
        lines.append(f"💥 %{int(discount_pct)} Indirim!")

    lines.append("")

    # Tıklanabilir link — fiyatın hemen altında
    if affiliate_url:
        if plain_link:
            lines.append(f'🔗{affiliate_url}')
        else:
            lines.append(f'🔗 <a href="{affiliate_url}">DIP FIYAT FIRSATA GIT!</a>')

    lines.append("")

    if condition:
        lines.append(f"📦 Durum: {condition}")
    if seller:
        lines.append(f"🚚 Satici: {seller}")
    if stock_note:
        lines.append(f"📦 Stok: {stock_note}")

    lines.append("")
    lines.append(SITE_FOOTER)
    lines.append("")
    lines.append(all_tags)
    lines.append("")
    lines.append("📢 Reklam & Affiliate içerik")

    return "\n".join(lines)


def generate_instagram(deal: dict) -> str:
    """Instagram caption — link içermez, bio'ya yönlendirir."""
    title          = deal.get("title", "")
    current_price  = deal.get("current_price", 0)
    original_price = deal.get("original_price", 0)
    discount_pct   = deal.get("discount_pct", 0)
    category       = deal.get("category", "default")
    stock_note     = deal.get("stock_note", "")

    cat_tags = CATEGORY_HASHTAGS.get(category, CATEGORY_HASHTAGS["default"])
    all_tags = BASE_HASHTAGS + "  " + "  ".join(cat_tags)

    lines = []
    lines.append(f"🔥 {title}")
    lines.append("")

    if original_price and original_price > current_price:
        lines.append(f"❌ Normal Fiyat: {original_price:,.0f} TL".replace(",", "."))

    lines.append(f"💰 {current_price:,.0f} TL".replace(",", "."))

    if discount_pct >= 1:
        lines.append(f"💥 %{int(discount_pct)} İndirim!")

    lines.append("")
    lines.append("🔗 Ürün linki bio'da → dipfiyatci.com")

    if stock_note:
        lines.append(f"📦 Stok: {stock_note}")

    lines.append("")
    lines.append(SITE_FOOTER)
    lines.append("")
    lines.append(all_tags)
    lines.append("")
    lines.append("📢 Reklam & Affiliate içerik")

    return "\n".join(lines)


if __name__ == "__main__":
    test_deal = {
        "title": "QCY H3 Pro Hybrid ANC Bluetooth 5.4 Kafaüstü Kablosuz Kulaklık Siyah",
        "current_price": 1506,
        "original_price": 2499,
        "discount_pct": 40,
        "asin": "B0DRSRH3GG",
        "category": "Electronics",
        "stock_note": "Stokta sadece 1 adet kaldı.",
    }
    print(generate(test_deal))
