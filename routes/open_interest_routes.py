from fastapi import APIRouter
from feed_handler import open_interest_data, lock
import logging

router = APIRouter()

@router.get("/open-interest")
def get_open_interest():
    logging.info("Received request for open interest data")
    with lock:
        data = open_interest_data.copy()
    return data
