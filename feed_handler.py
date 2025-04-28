import asyncio
import threading
import platform
import logging
import time
from datetime import datetime, timezone
from cryptofeed import FeedHandler
from cryptofeed.defines import L2_BOOK, TRADES, OPEN_INTEREST
from cryptofeed.exchanges import BinanceFutures
from requests.adapters import HTTPAdapter, Retry
import requests
from config import candles_collection, open_interest_collection, order_book_collection

# Global data and thread lock
lock = threading.Lock()
current_candle = None  # will be dict
last_candle = None
open_interest_data = {"value": None, "timestamp": None}
order_book_data = {"bids": [], "asks": []}

# Configure retries and timeouts
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

# Feed callbacks
async def trade_callback(trade, receipt_timestamp):
    global current_candle, last_candle
    ts = trade.timestamp  # float seconds since epoch
    price = float(trade.price)
    amount = float(trade.amount)

    # Determine the second (epoch int)
    sec = int(ts)
    with lock:
        if current_candle is None:
            # Initialize first candle
            current_candle = {
                "start_time": sec,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": amount
            }
            logging.info(f"Initialized first candle at {sec}")
        else:
            if sec != current_candle["start_time"]:
                # Candle has changed, move current to last, start new candle
                last_candle = current_candle
                current_candle = {
                    "start_time": sec,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": amount
                }
                # Save last candle to MongoDB
                try:
                    candles_collection.insert_one({
                        "type": "last_candle",
                        "data": last_candle
                    })
                    logging.info(f"Saved last candle to MongoDB at {sec}")
                except errors.PyMongoError as e:
                    logging.error(f"Error saving last candle to MongoDB: {e}")
            else:
                # Update current candle
                current_candle["close"] = price
                current_candle["high"] = max(current_candle["high"], price)
                current_candle["low"] = min(current_candle["low"], price)
                current_candle["volume"] += amount
                logging.info(f"Updated current candle at {sec}")

async def book_callback(book, receipt_timestamp):
    global order_book_data
    bids_dict = book.book.bids.to_dict()
    asks_dict = book.book.asks.to_dict()
    with lock:
        bids = []
        asks = []
        try:
            bid_items = list(bids_dict.items())
        except Exception:
            bid_items = []
        try:
            ask_items = list(asks_dict.items())
        except Exception:
            ask_items = []
        top_bids = list(reversed(bid_items))[:10]
        for price, size in top_bids:
            bids.append({"price": float(price), "amount": float(size)})
        top_asks = ask_items[:10]
        for price, size in top_asks:
            asks.append({"price": float(price), "amount": float(size)})
        order_book_data["bids"] = bids
        order_book_data["asks"] = asks
        logging.info("Updated order book data")

        # Save order book to MongoDB
        try:
            order_book_collection.insert_one({
                "timestamp": datetime.fromtimestamp(receipt_timestamp, tz=timezone.utc).isoformat(),
                "data": order_book_data
            })
            logging.info("Saved order book to MongoDB")
        except errors.PyMongoError as e:
            logging.error(f"Error saving order book to MongoDB: {e}")

async def oi_callback(oi, receipt_timestamp):
    global open_interest_data
    with lock:
        open_interest_data["value"] = float(oi.open_interest)
        open_interest_data["timestamp"] = datetime.fromtimestamp(receipt_timestamp, tz=timezone.utc).isoformat()
        logging.info("Updated open interest data")

        # Save open interest to MongoDB
        try:
            open_interest_collection.insert_one({
                "timestamp": open_interest_data["timestamp"],
                "value": open_interest_data["value"]
            })
            logging.info("Saved open interest to MongoDB")
        except errors.PyMongoError as e:
            logging.error(f"Error saving open interest to MongoDB: {e}")

# Background task to run the feed handler
def run_feed():
    while True:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        fh = FeedHandler()
        fh.add_feed(
            BinanceFutures(
                symbols=["BTC-USDT-PERP"],
                channels=[L2_BOOK, TRADES, OPEN_INTEREST],
                callbacks={
                    L2_BOOK: book_callback,
                    TRADES: trade_callback,
                    OPEN_INTEREST: oi_callback
                },
                http=http
            )
        )
        try:
            loop.run_until_complete(fh.run(install_signal_handlers=False))
        except Exception as e:
            logging.error(f"Error in feed handler: {e}")
            logging.info("Retrying in 5 seconds...")
            time.sleep(5)  # Wait before retrying
