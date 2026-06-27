"""
Railway worker — her gun 08:00, 12:30 ve 20:00'de (UTC+3) pipeline calistirir.
"""
import time
import logging
import os
import sys
from datetime import datetime
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

import config
from modules.database import init_db
from scheduler import run

TIMEZONE   = pytz.timezone("Europe/Istanbul")
POST_TIMES = config.POST_TIMES  # ["08:00", "12:30", "20:00"]

_last_run = {}


def _should_run(now: datetime) -> bool:
    hm = now.strftime("%H:%M")
    if hm not in POST_TIMES:
        return False
    date_str = now.strftime("%Y-%m-%d")
    key = f"{date_str}_{hm}"
    if _last_run.get(key):
        return False
    _last_run[key] = True
    return True


if __name__ == "__main__":
    init_db()
    logger.info("Railway worker baslatildi. Paylasim saatleri: %s", POST_TIMES)

    while True:
        now = datetime.now(TIMEZONE)
        if _should_run(now):
            logger.info("Pipeline tetiklendi: %s", now.strftime("%d.%m.%Y %H:%M"))
            try:
                run()
            except Exception as e:
                logger.error("Pipeline hatasi: %s", e, exc_info=True)
        time.sleep(30)
