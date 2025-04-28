from fastapi import FastAPI
from routes import candle_routes, open_interest_routes, order_book_routes
import threading
import feed_handler
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Include routers
app.include_router(candle_routes.router)
app.include_router(open_interest_routes.router)
app.include_router(order_book_routes.router)

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=feed_handler.run_feed, daemon=True)
    thread.start()
    logging.info("Started feed handler thread")

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
