"""
Dip Fiyat — Yonetim Paneli
Calistirmak icin: python dashboard/app.py
Tarayicida ac: http://localhost:5000
"""
import os
import sys
import json
import sqlite3
import subprocess
import threading
import queue
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

app = Flask(__name__)
app.secret_key = "dipfiyat2024"
logger = __import__("logging").getLogger(__name__)

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEDULER  = os.path.join(BASE_DIR, "scheduler.py")
PYTHON     = sys.executable

# Aktif pipeline log kuyrugu
log_queue = queue.Queue()
pipeline_running = threading.Event()


# ── YARDIMCI FONKSİYONLAR ──────────────────────────────────────────────────

def db():
    return sqlite3.connect(config.DB_PATH)


def get_recent_posts(limit=20):
    try:
        with db() as conn:
            rows = conn.execute(
                """SELECT asin, title, discount_pct, original_price, sale_price,
                          posted_at, video_path, ig_post_id
                   FROM posted_deals ORDER BY posted_at DESC LIMIT ?""",
                (limit,)
            ).fetchall()
        return rows
    except Exception:
        return []


def get_pipeline_stats():
    try:
        with db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM posted_deals").fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM posted_deals WHERE date(posted_at) = date('now')"
            ).fetchone()[0]
            last = conn.execute(
                "SELECT posted_at FROM posted_deals ORDER BY posted_at DESC LIMIT 1"
            ).fetchone()
        return {
            "total": total,
            "today": today,
            "last_post": last[0][:16].replace("T", " ") if last else "—"
        }
    except Exception:
        return {"total": 0, "today": 0, "last_post": "—"}


def get_scheduler_status():
    tasks = ["DipFiyat_Sabah", "DipFiyat_Ogle", "DipFiyat_Aksam"]
    result = []
    for task in tasks:
        try:
            out = subprocess.check_output(
                f'schtasks /query /tn "{task}" /fo LIST',
                shell=True, text=True, stderr=subprocess.DEVNULL,
                encoding="cp1254"
            )
            status   = "Aktif"   if "Ready" in out or "Haz" in out else "Pasif"
            next_run = ""
            for line in out.splitlines():
                if "Next Run" in line or "Sonraki" in line:
                    next_run = line.split(":", 1)[-1].strip()
            result.append({"name": task, "status": status, "next_run": next_run})
        except Exception:
            result.append({"name": task, "status": "Bulunamadi", "next_run": ""})
    return result


def run_pipeline_thread(url="", affiliate_url=""):
    """Pipeline'i arka planda calistirir, loglari kuyruga yazar."""
    pipeline_running.set()
    log_queue.put({"type": "start", "msg": f"Pipeline baslatildi — {datetime.now().strftime('%H:%M:%S')}"})

    cmd = [PYTHON, SCHEDULER]
    if url:
        cmd.append(url)
    if affiliate_url:
        cmd.append(affiliate_url)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=BASE_DIR,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for line in proc.stdout:
            line = line.strip()
            if line:
                log_queue.put({"type": "log", "msg": line})
        proc.wait()
        status = "tamamlandi" if proc.returncode == 0 else "hata"
        log_queue.put({"type": "end", "msg": f"Pipeline {status}.", "rc": proc.returncode})
    except Exception as e:
        logger.error("run_pipeline_thread hatasi: %s", e, exc_info=True)
        log_queue.put({"type": "end", "msg": f"Hata: {e}", "rc": 1})
    finally:
        pipeline_running.clear()  # Her durumda flag temizlenir


# ── ROTALAR ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    posts  = get_recent_posts(10)
    stats  = get_pipeline_stats()
    sched  = get_scheduler_status()
    return render_template("index.html",
                           posts=posts, stats=stats, sched=sched,
                           running=pipeline_running.is_set())


@app.route("/find_deals", methods=["POST"])
def find_deals():
    """Firsatlari bulur, dashboard'da gosterir — gondermez."""
    if pipeline_running.is_set():
        return jsonify({"ok": False, "msg": "Pipeline zaten calisiyor!"})

    def _find():
        pipeline_running.set()
        log_queue.put({"type": "start", "msg": "Firsatlar aranıyor — Amazon taranıyor (2-3 dakika)..."})
        try:
            import json, os
            finder_script = os.path.join(BASE_DIR, "find_deals_runner.py")

            proc = subprocess.Popen(
                [PYTHON, finder_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=BASE_DIR,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    log_queue.put({"type": "log", "msg": line})
            proc.wait()

            # Sonucu oku
            path = os.path.join(BASE_DIR, "data", "pending_deals.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    results = json.load(f)
                if results:
                    log_queue.put({"type": "end", "msg": f"{len(results)} firsat bulundu! 'Bulunan Firsatlari Gor' butonuna tiklayin.", "rc": 0})
                else:
                    log_queue.put({"type": "end", "msg": "Uygun firsat bulunamadi.", "rc": 1})
            else:
                log_queue.put({"type": "end", "msg": "Uygun firsat bulunamadi.", "rc": 1})

        except Exception as e:
            logger.error("find_deals thread hatasi: %s", e, exc_info=True)
            log_queue.put({"type": "end", "msg": f"Hata: {e}", "rc": 1})
        finally:
            pipeline_running.clear()  # Her durumda flag temizlenir

    t = threading.Thread(target=_find, daemon=True)
    t.start()
    return jsonify({"ok": True, "msg": "Firsatlar aranıyor..."})


@app.route("/pending_deals")
def pending_deals():
    """Bulunan firsatlari listeler."""
    import json, os
    path = os.path.join(BASE_DIR, "data", "pending_deals.json")
    if not os.path.exists(path):
        deals = []
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                deals = json.load(f)
        except Exception:
            deals = []
    return render_template("deals.html", deals=deals)


@app.route("/send_deal", methods=["POST"])
def send_deal():
    """Secilen firsati affiliate linki ile gonderir."""
    data          = request.json
    asin          = data.get("asin", "")
    affiliate_url = data.get("affiliate_url", "").strip()

    if not asin:
        return jsonify({"ok": False, "msg": "ASIN eksik."})
    # Affiliate link verilmemisse otomatik olustur
    if not affiliate_url:
        from modules.caption_writer import build_affiliate_url
        affiliate_url = build_affiliate_url(asin)

    import json, os, sys
    sys.path.insert(0, BASE_DIR)
    from modules.amazon_scraper import fetch_product
    from modules.image_creator  import create_image
    from modules.caption_writer import generate
    from modules.publisher      import publish_all
    from modules.database       import mark_posted, is_recently_posted
    from modules.github_pages   import update_page, get_recent_deals_for_page

    # Pending deals'den bul
    path = os.path.join(BASE_DIR, "data", "pending_deals.json")
    deal = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            deals = json.load(f)
        for d in deals:
            if d["asin"] == asin:
                deal = d
                break

    if not deal:
        deal = fetch_product(asin)

    if not deal or deal.get("current_price", 0) == 0:
        return jsonify({"ok": False, "msg": "Urun bilgisi alinamadi."})

    if is_recently_posted(asin):
        return jsonify({"ok": False, "msg": "Bu urun son 30 gun icinde paylasıldi."})

    try:
        image_path = create_image(deal)
        caption    = generate(deal, affiliate_url)
        results    = publish_all(image_path=image_path, caption=caption,
                                 affiliate_url=affiliate_url,
                                 public_image_url=deal.get("image_url", ""),
                                 deal=deal)
        if any(results.values()):
            mark_posted(asin, deal["title"], deal["discount_pct"],
                        deal["original_price"], deal["current_price"], image_path,
                        image_url=deal.get("image_url", ""))
            update_page(get_recent_deals_for_page(limit=50))
            return jsonify({"ok": True, "msg": "Gonderildi ve GitHub Pages guncellendi!"})
        else:
            return jsonify({"ok": False, "msg": "Hicbir kanala gonderilemedi."})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/run", methods=["POST"])
def run_auto():
    if pipeline_running.is_set():
        return jsonify({"ok": False, "msg": "Pipeline zaten calisiyor!"})
    t = threading.Thread(target=run_pipeline_thread, daemon=True)
    t.start()
    return jsonify({"ok": True, "msg": "Pipeline baslatildi."})


@app.route("/run_url", methods=["POST"])
def run_url():
    if pipeline_running.is_set():
        return jsonify({"ok": False, "msg": "Pipeline zaten calisiyor!"})

    import re
    url           = request.json.get("url", "").strip()
    affiliate_url = request.json.get("affiliate_url", "").strip()

    # Sadece affiliate link verilmisse, onu URL olarak da kullan
    if not url and affiliate_url:
        url = affiliate_url
    elif not url:
        return jsonify({"ok": False, "msg": "URL veya affiliate link girin."})

    # URL'den ASIN cikart, Amazon urun URL'i olustur
    m = re.search(r'/dp/([A-Z0-9]{10})', url)
    if m:
        asin = m.group(1)
        url  = f"https://www.amazon.com.tr/dp/{asin}"

        # 7 gunluk engel varsa otomatik kaldir
        from modules.database import is_recently_posted
        from datetime import datetime, timedelta
        if is_recently_posted(asin):
            with db() as conn:
                old_date = (datetime.utcnow() - timedelta(days=60)).isoformat()
                conn.execute('UPDATE posted_deals SET posted_at = ? WHERE asin = ?', (old_date, asin))
                conn.commit()

    t = threading.Thread(target=run_pipeline_thread, args=(url,), kwargs={"affiliate_url": affiliate_url}, daemon=True)
    t.start()
    return jsonify({"ok": True, "msg": "Urun isleniyor..."})


@app.route("/manual_post", methods=["POST"])
def manual_post():
    """Kullanicinin elle girdigi bilgilerle gorsel olustur ve Telegram'a gonder."""
    from modules.image_creator  import create_image
    from modules.caption_writer import generate, build_affiliate_url
    from modules.publisher      import publish_all
    from modules.database       import mark_posted

    data = request.json
    deal = {
        "asin":           data.get("asin", "MANUEL"),
        "title":          data.get("title", ""),
        "current_price":  float(data.get("current_price", 0)),
        "original_price": float(data.get("original_price", 0)),
        "discount_pct":   float(data.get("discount_pct", 0)),
        "image_url":      data.get("image_url", ""),
        "condition":      data.get("condition", "Yeni"),
        "stock_note":     data.get("stock_note", ""),
        "seller":         data.get("seller", ""),
        "category":       data.get("category", "default"),
    }

    # Indirim hesapla
    if deal["discount_pct"] == 0 and deal["original_price"] > deal["current_price"] > 0:
        deal["discount_pct"] = round(
            (deal["original_price"] - deal["current_price"]) / deal["original_price"] * 100
        )

    try:
        img_path      = create_image(deal)
        affiliate_url = build_affiliate_url(deal["asin"]) if deal["asin"] != "MANUEL" else data.get("affiliate_url", "")
        caption       = generate(deal, affiliate_url)
        results       = publish_all(image_path=img_path, caption=caption, affiliate_url=affiliate_url, deal=deal)

        if any(results.values()):
            mark_posted(deal["asin"], deal["title"], deal["discount_pct"],
                        deal["original_price"], deal["current_price"], img_path,
                        image_url=deal.get("image_url", ""))
            return jsonify({"ok": True, "msg": "Gonderildi!", "results": results})
        else:
            return jsonify({"ok": False, "msg": "Hicbir kanala gonderilemedi.", "results": results})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/log_stream")
def log_stream():
    """SSE ile canli log akisi."""
    def generate():
        yield "data: {\"msg\": \"Baglandi.\"}\n\n"
        while True:
            try:
                item = log_queue.get(timeout=30)
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                if item.get("type") == "end":
                    break
            except queue.Empty:
                yield "data: {\"type\": \"ping\"}\n\n"
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/status")
def status():
    return jsonify({
        "running": pipeline_running.is_set(),
        "stats":   get_pipeline_stats(),
    })


@app.route("/reset", methods=["POST"])
def reset():
    """Pipeline bayrağını sıfırla."""
    pipeline_running.clear()
    return jsonify({"ok": True, "msg": "Sıfırlandı."})


@app.route("/delete_post/<asin>", methods=["POST"])
def delete_post(asin):
    try:
        with db() as conn:
            conn.execute("DELETE FROM posted_deals WHERE asin = ?", (asin,))
            conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/reset_block/<asin>", methods=["POST"])
def reset_block(asin):
    """Ürünün engelini kaldırır — kaydı silmez, posted_at'i geçmişe çeker."""
    try:
        from datetime import datetime, timedelta
        old_date = (datetime.utcnow() - timedelta(days=60)).isoformat()
        with db() as conn:
            conn.execute("UPDATE posted_deals SET posted_at = ? WHERE asin = ?", (old_date, asin))
            conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/wa_caption/<asin>")
def wa_caption(asin):
    """WhatsApp icin HTML tagsiz temiz metin uretir."""
    import sys
    sys.path.insert(0, BASE_DIR)
    from modules.caption_writer import build_affiliate_url

    try:
        with db() as conn:
            row = conn.execute(
                "SELECT title, discount_pct, original_price, sale_price FROM posted_deals WHERE asin=?", (asin,)
            ).fetchone()
    except Exception:
        return jsonify({"ok": False, "msg": "Urun bulunamadi."})

    if not row:
        return jsonify({"ok": False, "msg": "Urun bulunamadi."})

    title, discount_pct, orig, sale = row
    affiliate_url = build_affiliate_url(asin)

    lines = []
    lines.append(f"🔥 {title}")
    lines.append("")
    if orig and orig > sale:
        lines.append(f"❌ Normal Fiyat: {orig:,.0f} TL".replace(",", "."))
    lines.append(f"💰 {sale:,.0f} TL".replace(",", "."))
    if discount_pct and discount_pct >= 1:
        lines.append(f"💥 %{int(discount_pct)} İndirim!")
    lines.append("")
    lines.append(f"🛒 {affiliate_url}")
    lines.append("")
    lines.append("🌐 Tüm fırsatlar için → dipfiyatci.com")
    lines.append("")
    lines.append("#dipfiyat #amazon #amazontürkiye #indirim #kampanya #fırsat #ucuz #alışveriş #teklif")
    lines.append("")
    lines.append("📢 Reklam & Affiliate içerik")

    return jsonify({"ok": True, "text": "\n".join(lines)})


@app.route("/instagram")
def instagram():
    """Son paylasimlar icin gorsel + caption hazirlar."""
    import sys
    sys.path.insert(0, BASE_DIR)
    from modules.caption_writer import generate, build_affiliate_url

    posts = get_recent_posts(10)
    result = []
    for p in posts:
        asin        = p[0]
        title       = p[1]
        discount    = p[2]
        orig_price  = p[3]
        sale_price  = p[4]
        posted_at   = p[5]
        video_path  = p[6]

        # Caption olustur
        deal = {
            "asin":           asin,
            "title":          title,
            "current_price":  sale_price,
            "original_price": orig_price,
            "discount_pct":   discount,
            "category":       "default",
            "condition":      "",
            "stock_note":     "",
            "seller":         "",
        }
        affiliate_url = build_affiliate_url(asin)
        caption = generate(deal, affiliate_url, plain_link=True)

        # Gorsel yolu
        img_filename = os.path.basename(video_path) if video_path else ""
        img_exists   = os.path.exists(video_path) if video_path else False

        result.append({
            "asin":       asin,
            "title":      title[:60],
            "caption":    caption,
            "img_path":   video_path,
            "img_file":   img_filename,
            "img_exists": img_exists,
            "posted_at":  posted_at[:16].replace("T", " ") if posted_at else "",
        })

    return render_template("instagram.html", posts=result)


@app.route("/image/<path:filename>")
def serve_image(filename):
    """Gorsel dosyasini tarayiciya gonderir."""
    from flask import send_file
    img_path = os.path.join(BASE_DIR, "output", "images", filename)
    if os.path.exists(img_path):
        return send_file(img_path, mimetype="image/png")
    return "Gorsel bulunamadi", 404


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  DIP FIYAT YONETIM PANELI")
    print("  Tarayicida ac: http://localhost:5001")
    print("="*50 + "\n")
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)
