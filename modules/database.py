import sqlite3
import logging
from datetime import datetime, timedelta
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


def get_connection():
    return sqlite3.connect(config.DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posted_deals (
                asin           TEXT PRIMARY KEY,
                title          TEXT,
                discount_pct   REAL,
                original_price REAL,
                sale_price     REAL,
                posted_at      TEXT,
                video_path     TEXT,
                ig_post_id     TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at   TEXT,
                finished_at  TEXT,
                deals_found  INTEGER DEFAULT 0,
                posted       INTEGER DEFAULT 0,
                error        TEXT
            )
        """)
        conn.commit()
    logger.info("Veritabanı hazır: %s", config.DB_PATH)


def is_recently_posted(asin: str) -> bool:
    cutoff = (datetime.utcnow() - timedelta(days=config.REPOST_DAYS)).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT posted_at FROM posted_deals WHERE asin = ? AND posted_at > ?",
            (asin, cutoff)
        ).fetchone()
    return row is not None


def mark_posted(asin: str, title: str, discount_pct: float,
                original_price: float, sale_price: float,
                video_path: str = "", ig_post_id: str = "", image_url: str = ""):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        # image_url sütunu yoksa ekle (mevcut DB'ler için)
        try:
            conn.execute("ALTER TABLE posted_deals ADD COLUMN image_url TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass
        conn.execute("""
            INSERT OR REPLACE INTO posted_deals
                (asin, title, discount_pct, original_price, sale_price, posted_at, video_path, ig_post_id, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (asin, title, discount_pct, original_price, sale_price, now, video_path, ig_post_id, image_url))
        conn.commit()
    logger.info("Veritabanına kaydedildi: %s", asin)


def start_run() -> int:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO pipeline_runs (started_at) VALUES (?)", (now,)
        )
        conn.commit()
        return cur.lastrowid


def finish_run(run_id: int, deals_found: int, posted: int, error: str = ""):
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute("""
            UPDATE pipeline_runs
               SET finished_at = ?, deals_found = ?, posted = ?, error = ?
             WHERE run_id = ?
        """, (now, deals_found, posted, error, run_id))
        conn.commit()


def recent_posts(limit: int = 10) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT asin, title, discount_pct, sale_price, posted_at FROM posted_deals ORDER BY posted_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Veritabani basariyla olusturuldu.")
    print("Konum:", config.DB_PATH)
