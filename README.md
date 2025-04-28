# FastAPI Cryptofeed

Welcome to **FastAPI Cryptofeed**, a robust and scalable project designed to fetch and serve real-time cryptocurrency data using FastAPI and MongoDB. This project is perfect for developers looking to build financial applications, trading bots, or simply explore the world of cryptocurrency data.

## 🚀 Features

- **Real-time Data**: Fetch live cryptocurrency data using the Binance Futures API.
- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **MongoDB**: Store and manage data efficiently with MongoDB, a NoSQL database.
- **Modular Structure**: Organized codebase with separate modules for routes, feed handling, and configuration.
- **Easy Setup**: Simple instructions to get you up and running quickly.

## 📦 Installation

### Prerequisites

- Python 3.7+
- MongoDB (local or cloud instance)
- Git


# 📁 Directory Structure

Below is the project layout rendered as a plain-text tree.  


```text
project_root/
│
├── main.py                    # 🏁  Application entry point
├── config.py                  # ⚙️   MongoDB & other configuration
├── feed_handler.py            # 🔄  Feed-handler logic
│
└── routes/                    # 🌐  FastAPI route handlers
    ├── __init__.py            # Package initializer
    ├── candle_routes.py       # 📈  Candle-data endpoints
    ├── open_interest_routes.py# 📊  Open-interest endpoints
    └── order_book_routes.py   # 📚  Order-book endpoints

