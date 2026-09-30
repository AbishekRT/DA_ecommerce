"""
extensions.py
Centralised setup for MongoClient and Flask-Login.
Imported by app.py and all route blueprints.
"""

from pymongo import MongoClient
from flask_login import LoginManager
import os

# ---------------------------------------------------------------------------
# MongoDB connection
# ---------------------------------------------------------------------------
client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("DATABASE_NAME", "projector_ecommerce")]

# Convenience handles — imported wherever a collection is needed
users_col      = db["users"]
categories_col = db["categories"]
products_col   = db["products"]
carts_col      = db["carts"]
orders_col     = db["orders"]
rentals_col    = db["rentals"]

# ---------------------------------------------------------------------------
# Flask-Login
# ---------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.login_view = "auth.login"   # redirect unauthorized users here
login_manager.login_message_category = "warning"