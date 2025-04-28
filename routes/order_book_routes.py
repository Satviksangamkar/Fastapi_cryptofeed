from fastapi import APIRouter
from feed_handler import order_book_data, lock
import logging

router = APIRouter()

@router.get("/order-book")
def get_order_book():
    logging.info("Received request for order book data")
    with lock:
        data = order_book_data.copy()
    return data
