"""
extensions.py
Centralised setup for MongoClient and Flask-Login.
Imported by app.py and all route blueprints.
"""

from pymongo import MongoClient
from flask_login import LoginManager
import os

try:
    import certifi
    ca = certifi.where()
except Exception:
    ca = None

# ---------------------------------------------------------------------------
# MongoDB connection (Local, VPS, and Cloud Atlas Support)
# ---------------------------------------------------------------------------
mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client_kwargs = {
    "serverSelectionTimeoutMS": 5000,
    "connectTimeoutMS": 5000,
}
if "mongodb+srv://" in mongo_uri and ca:
    client_kwargs["tlsCAFile"] = ca

client = MongoClient(mongo_uri, **client_kwargs)

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