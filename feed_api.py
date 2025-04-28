import asyncio
import threading
import platform
import logging
import time
from datetime import datetime, timezone
from fastapi import FastAPI
from cryptofeed import FeedHandler
from cryptofeed.defines import L2_BOOK, TRADES, OPEN_INTEREST
from cryptofeed.exchanges import BinanceFutures
from requests.adapters import HTTPAdapter, Retry
import requests
from pymongo import MongoClient, errors

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MongoDB connection setup
MONGO_URI = "mongodb+srv://satvik:Stankarrk@satvik.kimjuo9.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)

# Database and collections setup
db_name = "cryptofeed_db"
if db_name not in client.list_database_names():
    logging.info(f"Database '{db_name}' does not exist. Creating new database.")
db = client[db_name]

# Collections
candles_collection = db.candles
open_interest_collection = db.open_interest
order_book_collection = db.order_book

# Apply Windows event loop policy fix if necessary
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Optionally apply nest_asyncio for nested event loop if needed
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

app = FastAPI()

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

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=run_feed, daemon=True)
    thread.start()
    logging.info("Started feed handler thread")

    # Test MongoDB connection
    try:
        client.admin.command('ping')
        logging.info("Connected to MongoDB successfully")
    except errors.PyMongoError as e:
        logging.error(f"Failed to connect to MongoDB: {e}")

@app.get("/")
def read_root():
    logging.info("Received request for root endpoint")
    return {
        "message": "Welcome to the Binance Futures Data API",
        "endpoints": {
            "/candle": "Get current and last completed 1-second candle",
            "/open-interest": "Get latest open interest data",
            "/order-book": "Get top-10 bids and asks from the order book"
        }
    }

@app.get("/candle")
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

@app.get("/open-interest")
def get_open_interest():
    logging.info("Received request for open interest data")
    with lock:
        data = open_interest_data.copy()
    return data

@app.get("/order-book")
def get_order_book():
    logging.info("Received request for order book data")
    with lock:
        data = order_book_data.copy()
    return data
