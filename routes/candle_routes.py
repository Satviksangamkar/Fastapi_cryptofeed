from fastapi import APIRouter
from feed_handler import current_candle, last_candle, lock
import logging
from datetime import datetime, timezone

router = APIRouter()

@router.get("/candle")
def get_candle():
    logging.info("Received request for candle data")
    with lock:
        curr = current_candle.copy() if current_candle else None
        last = last_candle.copy() if last_candle else None
    def format_candle(c):
        if not c:
            return None
        dt = datetime.fromtimestamp(c["start_time"], tz=timezone.utc)
        return {
            "start_time": dt.isoformat(),
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c["volume"]
        }
    return {
        "current": format_candle(curr),
        "last": format_candle(last)
    }
