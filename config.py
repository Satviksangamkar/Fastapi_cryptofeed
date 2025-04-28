from pymongo import MongoClient, errors
import logging

# MongoDB connection setup
MONGO_URI = "mongodb+srv://satvik:Stankarrk@satvik.kimjuo9.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)

# Database and collections setup
db_name = "cryptofeed_db"
if db_name not in client.list_database_names():
    logging.info(f"Database '{db_name}' does not exist. Creating new database.")
db = client[db_name]

# Initialize collections
candles_collection = db.candles
open_interest_collection = db.open_interest
order_book_collection = db.order_book
