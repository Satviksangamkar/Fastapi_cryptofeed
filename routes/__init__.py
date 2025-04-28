from fastapi import APIRouter
from .candle_routes import router as candle_router
from .open_interest_routes import router as open_interest_router
from .order_book_routes import router as order_book_router

router = APIRouter()

router.include_router(candle_router, prefix="/candle", tags=["candle"])
router.include_router(open_interest_router, prefix="/open-interest", tags=["open-interest"])
router.include_router(order_book_router, prefix="/order-book", tags=["order-book"])
