"""
seed.py
Seeds the MongoDB database with:
  - 1 admin user
  - 2 sample customer users
  - 5 product categories
  - 18 projector products with realistic specs

Also creates all required indexes explicitly.

Run with:  python seed.py
"""

from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
db     = client[os.getenv("DATABASE_NAME", "projector_ecommerce")]


def drop_all():
    """Drop all collections for a clean seed."""
    for col in ["users", "categories", "products", "carts", "orders", "rentals"]:
        db[col].drop()
    print("[seed] Dropped all collections.")


def create_indexes():
    """
    Create all indexes explicitly — never rely on MongoDB's default _id index alone.
    Each index serves a specific query pattern documented below.
    """
    # Unique index on users.email — enforces no duplicate accounts
    # and supports fast find_one({"email": ...}) lookups at login/register
    db["users"].create_index([("email", ASCENDING)], unique=True)

    # Index on products.category_id — supports filtering the catalog by category
    db["products"].create_index([("category_id", ASCENDING)])

    # Index on products.type — supports filtering by "sell"/"rent"/"both"
    db["products"].create_index([("type", ASCENDING)])

    # Compound index on rentals — supports the availability-conflict query:
    #   find({product_id: X, status: ..., start_date: {$lt: Y}, end_date: {$gt: Z}})
    # product_id first (equality filter), then start_date and end_date (range filters)
    db["rentals"].create_index([
        ("product_id", ASCENDING),
        ("start_date",  ASCENDING),
        ("end_date",    ASCENDING),
    ])

    # Index on orders.user_id — supports fetching a customer's order history
    db["orders"].create_index([("user_id", ASCENDING)])

    # Descending index on orders.created_at — supports sorting order history newest-first
    db["orders"].create_index([("created_at", DESCENDING)])

    print("[seed] Indexes created.")


def seed_users():
    now = datetime.now(timezone.utc)
    users = [
        {
            "email":         "admin@projectorshop.com",
            "password_hash": generate_password_hash("ProjAdmin#2026!Secure"),
            "name":          "Admin Manager",
            "role":          "admin",
            "created_at":    now,
        },
        {
            "email":         "staff@projectorshop.com",
            "password_hash": generate_password_hash("ProjStaff#2026!Secure"),
            "name":          "Sarah (Rental Staff)",
            "role":          "staff",
            "created_at":    now,
        },
        {
            "email":         "alice@example.com",
            "password_hash": generate_password_hash("Alice#Pass2026$"),
            "name":          "Alice Johnson",
            "role":          "customer",
            "created_at":    now,
        },
        {
            "email":         "bob@example.com",
            "password_hash": generate_password_hash("Bob#ProjStore99*"),
            "name":          "Bob Smith",
            "role":          "customer",
            "created_at":    now,
        },
    ]
    result = db["users"].insert_many(users)
    print(f"[seed] Inserted {len(result.inserted_ids)} users.")
    return result.inserted_ids


def seed_categories():
    categories = [
        {"name": "Home Cinema",         "description": "High-brightness projectors for home theatre setups."},
        {"name": "Business / Portable", "description": "Compact projectors for meetings and travel."},
        {"name": "4K Ultra HD",         "description": "4K resolution projectors for crisp, detailed images."},
        {"name": "Ultra Short Throw",   "description": "Projectors that work within inches of the screen."},
        {"name": "Outdoor / Event",     "description": "High-lumen projectors for outdoor screenings and events."},
    ]
    result = db["categories"].insert_many(categories)
    print(f"[seed] Inserted {len(result.inserted_ids)} categories.")
    return result.inserted_ids   # returns list of 5 ObjectIds in order


def seed_products(cat_ids):
    home, biz, uhd, ust, outdoor = cat_ids
    now = datetime.now(timezone.utc)

    products = [
        # ---- Home Cinema ----
        {
            "name": "Epson Home Cinema 2350",
            "brand": "Epson",
            "category_id": home,
            "type": "both",
            "sale_price": 389900.00,
            "rent_price_per_day": 13500.00,
            "stock_qty": 8,
            "image_url": "/static/images/products/epson_hc2350.jpg",
            "description": "Full HD 3LCD home cinema projector with 4500 lumens. Ideal for dedicated home theatre rooms.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 4500,
                "throw_distance": "1.0m - 5.5m",
                "connectivity": ["HDMI", "USB", "WiFi", "Bluetooth"],
            },
            "created_at": now,
        },
        {
            "name": "BenQ HT3550i",
            "brand": "BenQ",
            "category_id": home,
            "type": "sell",
            "sale_price": 509900.00,
            "rent_price_per_day": None,
            "stock_qty": 5,
            "image_url": "/static/images/products/benq_ht3550i.jpg",
            "description": "4K HDR DLP home projector with 2000 ANSI lumens and wide colour gamut for cinematic visuals.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2000,
                "throw_distance": "1.2m - 7.2m",
                "connectivity": ["HDMI 2.0", "USB", "Android TV"],
            },
            "created_at": now,
        },
        {
            "name": "Sony VPL-VW325ES",
            "brand": "Sony",
            "category_id": home,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 36000.00,
            "stock_qty": 3,
            "image_url": "/static/images/products/sony_vpl.jpg",
            "description": "Premium Sony 4K SXRD projector for a true cinema-at-home experience. Available for rent only.",
            "specs": {
                "resolution": "4096x2160 (4K)",
                "brightness_lumens": 1500,
                "throw_distance": "1.5m - 8.0m",
                "connectivity": ["HDMI", "RS-232C", "IR"],
            },
            "created_at": now,
        },
        # ---- Business / Portable ----
        {
            "name": "Anker Nebula Capsule 3",
            "brand": "Anker",
            "category_id": biz,
            "type": "both",
            "sale_price": 179900.00,
            "rent_price_per_day": 6000.00,
            "stock_qty": 12,
            "image_url": "/static/images/products/nebula_capsule.jpg",
            "description": "Portable mini projector the size of a soda can. Built-in battery and Android TV.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 300,
                "throw_distance": "0.8m - 3.5m",
                "connectivity": ["HDMI", "USB-C", "WiFi", "Bluetooth", "Android TV"],
            },
            "created_at": now,
        },
        {
            "name": "Optoma ML1080ST",
            "brand": "Optoma",
            "category_id": biz,
            "type": "both",
            "sale_price": 269900.00,
            "rent_price_per_day": 9000.00,
            "stock_qty": 9,
            "image_url": "/static/images/products/optoma_ml1080.jpg",
            "description": "Ultra-compact Full HD laser projector weighing just 0.9 kg. Perfect for business travel.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 1000,
                "throw_distance": "0.7m - 4.0m",
                "connectivity": ["HDMI", "USB-A", "USB-C"],
            },
            "created_at": now,
        },
        {
            "name": "Epson EB-W52",
            "brand": "Epson",
            "category_id": biz,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 5400.00,
            "stock_qty": 15,
            "image_url": "/static/images/products/epson_ebw52.jpg",
            "description": "WXGA business projector with 4000 lumens. Ideal for meeting rooms and conference presentations.",
            "specs": {
                "resolution": "1280x800 (WXGA)",
                "brightness_lumens": 4000,
                "throw_distance": "0.9m - 12.3m",
                "connectivity": ["HDMI", "VGA", "USB", "LAN"],
            },
            "created_at": now,
        },
        # ---- 4K Ultra HD ----
        {
            "name": "LG CineBeam HU85LA",
            "brand": "LG",
            "category_id": uhd,
            "type": "both",
            "sale_price": 899900.00,
            "rent_price_per_day": 28000.00,
            "stock_qty": 4,
            "image_url": "/static/images/products/lg_cinebeam.jpg",
            "description": "4K UHD triple laser ultra short throw projector with 4000 ANSI lumens and webOS smart platform.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 4000,
                "throw_distance": "0.12m - 0.4m",
                "connectivity": ["HDMI 2.0", "USB", "WiFi", "Bluetooth", "webOS"],
            },
            "created_at": now,
        },
        {
            "name": "BenQ W4000i",
            "brand": "BenQ",
            "category_id": uhd,
            "type": "sell",
            "sale_price": 749900.00,
            "rent_price_per_day": None,
            "stock_qty": 6,
            "image_url": "/static/images/products/benq_w4000i.jpg",
            "description": "4K DLP projector with 3200 lumens, HDR Pro, and Android TV built in.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 3200,
                "throw_distance": "1.5m - 8.0m",
                "connectivity": ["HDMI 2.0", "USB", "Android TV", "WiFi"],
            },
            "created_at": now,
        },
        {
            "name": "Optoma UHD50X",
            "brand": "Optoma",
            "category_id": uhd,
            "type": "both",
            "sale_price": 404900.00,
            "rent_price_per_day": 16000.00,
            "stock_qty": 7,
            "image_url": "/static/images/products/optoma_uhd50x.jpg",
            "description": "4K UHD projector with 240Hz refresh rate and enhanced gaming features. 3400 ANSI lumens.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 3400,
                "throw_distance": "1.2m - 7.0m",
                "connectivity": ["HDMI 2.0", "VGA", "USB"],
            },
            "created_at": now,
        },
        # ---- Ultra Short Throw ----
        {
            "name": "Samsung The Premiere LSP9T",
            "brand": "Samsung",
            "category_id": ust,
            "type": "both",
            "sale_price": 1949900.00,
            "rent_price_per_day": 45000.00,
            "stock_qty": 2,
            "image_url": "/static/images/products/samsung_lsp9t.jpg",
            "description": "Triple laser 4K UST projector with Tizen OS. Projects 130 inches from 25cm away.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 4000,
                "throw_distance": "0.10m - 0.30m",
                "connectivity": ["HDMI 2.0", "USB", "WiFi", "Bluetooth", "Tizen OS"],
            },
            "created_at": now,
        },
        {
            "name": "Epson LS500",
            "brand": "Epson",
            "category_id": ust,
            "type": "sell",
            "sale_price": 1049900.00,
            "rent_price_per_day": None,
            "stock_qty": 4,
            "image_url": "/static/images/products/epson_ls500.jpg",
            "description": "Epson laser ultra-short-throw with Android TV. 4000 lumens for a bright image in any room.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 4000,
                "throw_distance": "0.08m - 0.35m",
                "connectivity": ["HDMI", "USB", "Android TV", "WiFi", "Bluetooth"],
            },
            "created_at": now,
        },
        {
            "name": "Hisense PX1-PRO",
            "brand": "Hisense",
            "category_id": ust,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 24000.00,
            "stock_qty": 3,
            "image_url": "/static/images/products/hisense_px1.jpg",
            "description": "4K TriChroma laser UST projector with Dolby Vision. Premium image quality at short throw.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2200,
                "throw_distance": "0.10m - 0.25m",
                "connectivity": ["HDMI 2.0", "USB", "WiFi", "Bluetooth"],
            },
            "created_at": now,
        },
        # ---- Outdoor / Event ----
        {
            "name": "Barco DP2K-10S",
            "brand": "Barco",
            "category_id": outdoor,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 105000.00,
            "stock_qty": 2,
            "image_url": "/static/images/products/barco_dp2k.jpg",
            "description": "Professional digital cinema projector with 10,000 lumens. Built for outdoor events and large venues.",
            "specs": {
                "resolution": "2048x1080 (2K DCI)",
                "brightness_lumens": 10000,
                "throw_distance": "5.0m - 30.0m",
                "connectivity": ["HDMI", "DVI", "SDI", "LAN"],
            },
            "created_at": now,
        },
        {
            "name": "Optoma ZH606",
            "brand": "Optoma",
            "category_id": outdoor,
            "type": "both",
            "sale_price": 1139900.00,
            "rent_price_per_day": 33000.00,
            "stock_qty": 3,
            "image_url": "/static/images/products/optoma_zh606.jpg",
            "description": "6000-lumen Full HD laser projector for outdoor cinema and large venue events.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 6000,
                "throw_distance": "2.5m - 20.0m",
                "connectivity": ["HDMI", "VGA", "HDBaseT", "LAN"],
            },
            "created_at": now,
        },
        {
            "name": "Christie Roadster HD20K-J",
            "brand": "Christie",
            "category_id": outdoor,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 150000.00,
            "stock_qty": 1,
            "image_url": "/static/images/products/christie_hd20k.jpg",
            "description": "20,000 lumen 1080p 3-chip DLP projector. Industry standard for large outdoor concerts and stadium events.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 20000,
                "throw_distance": "10.0m - 80.0m",
                "connectivity": ["HDMI", "DVI-D", "3G-SDI", "LAN"],
            },
            "created_at": now,
        },
        {
            "name": "Epson EH-LS12000B",
            "brand": "Epson",
            "category_id": home,
            "type": "both",
            "sale_price": 1499900.00,
            "rent_price_per_day": 19000.00,
            "stock_qty": 2,
            "image_url": "/static/images/products/epson_ls12000b.jpg",
            "description": "Epson flagship 4K laser projector with 2700 lumens and advanced HDR support. Premium home cinema.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2700,
                "throw_distance": "1.3m - 8.7m",
                "connectivity": ["HDMI 2.1", "USB", "LAN", "RS-232C"],
            },
            "created_at": now,
        },
        {
            "name": "ViewSonic X100-4K+",
            "brand": "ViewSonic",
            "category_id": uhd,
            "type": "both",
            "sale_price": 539900.00,
            "rent_price_per_day": 18000.00,
            "stock_qty": 5,
            "image_url": "/static/images/products/viewsonic_x100.jpg",
            "description": "4K LED smart projector with built-in Harman Kardon speakers and 2900 ANSI lumens.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2900,
                "throw_distance": "1.5m - 8.5m",
                "connectivity": ["HDMI 2.0", "USB", "WiFi", "Bluetooth", "Android TV"],
            },
            "created_at": now,
        },
        {
            "name": "XGIMI Horizon Ultra",
            "brand": "XGIMI",
            "category_id": home,
            "type": "both",
            "sale_price": 1179900.00,
            "rent_price_per_day": 15000.00,
            "stock_qty": 6,
            "image_url": "/static/images/products/xgimi_horizon.jpg",
            "description": "4K Dual Light projector combining laser and LED for vibrant colour. Includes Android TV 11.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2300,
                "throw_distance": "1.4m - 8.0m",
                "connectivity": ["HDMI 2.0", "USB", "WiFi 6", "Bluetooth 5.0", "Android TV"],
            },
            "created_at": now,
        },
    ]
    result = db["products"].insert_many(products)
    print(f"[seed] Inserted {len(result.inserted_ids)} products.")
    return result.inserted_ids


def seed_orders(user_ids, product_ids):
    """
    Seed realistic sample orders.
    EMBEDDING: items array embeds product names, quantities, and price snapshots.
    REFERENCING: user_id references the users collection.
    """
    now = datetime.now(timezone.utc)
    alice_id = user_ids[2]  # alice@example.com
    bob_id   = user_ids[3]  # bob@example.com

    orders = [
        {
            "user_id": alice_id,
            "items": [
                {
                    "product_id": product_ids[0],  # Epson Home Cinema 2350
                    "name": "Epson Home Cinema 2350",
                    "qty": 1,
                    "unit_price": 389900.00,
                    "subtotal": 389900.00,
                }
            ],
            "total": 389900.00,
            "status": "completed",
            "created_at": now - timedelta(days=12),
        },
        {
            "user_id": bob_id,
            "items": [
                {
                    "product_id": product_ids[3],  # Anker Nebula Capsule 3
                    "name": "Anker Nebula Capsule 3",
                    "qty": 2,
                    "unit_price": 179900.00,
                    "subtotal": 359800.00,
                },
                {
                    "product_id": product_ids[1],  # BenQ HT3550i
                    "name": "BenQ HT3550i",
                    "qty": 1,
                    "unit_price": 509900.00,
                    "subtotal": 509900.00,
                },
            ],
            "total": 869700.00,
            "status": "confirmed",
            "created_at": now - timedelta(days=6),
        },
        {
            "user_id": alice_id,
            "items": [
                {
                    "product_id": product_ids[6],  # LG CineBeam HU85LA
                    "name": "LG CineBeam HU85LA",
                    "qty": 1,
                    "unit_price": 899900.00,
                    "subtotal": 899900.00,
                }
            ],
            "total": 899900.00,
            "status": "completed",
            "created_at": now - timedelta(days=2),
        },
        {
            "user_id": bob_id,
            "items": [
                {
                    "product_id": product_ids[16],  # ViewSonic X100-4K+
                    "name": "ViewSonic X100-4K+",
                    "qty": 1,
                    "unit_price": 539900.00,
                    "subtotal": 539900.00,
                }
            ],
            "total": 539900.00,
            "status": "pending",
            "created_at": now - timedelta(hours=3),
        },
    ]

    result = db["orders"].insert_many(orders)
    print(f"[seed] Inserted {len(result.inserted_ids)} orders.")
    return result.inserted_ids


def seed_rentals(user_ids, product_ids):
    """
    Seed realistic sample rental bookings.
    REFERENCING: product_id and user_id are references to products and users collections.
    """
    now = datetime.now(timezone.utc)
    alice_id = user_ids[2]  # alice@example.com
    bob_id   = user_ids[3]  # bob@example.com

    rentals = [
        {
            "user_id": alice_id,
            "product_id": product_ids[2],  # Sony VPL-VW325ES
            "start_date": (now - timedelta(days=20)).strftime("%Y-%m-%d"),
            "end_date":   (now - timedelta(days=15)).strftime("%Y-%m-%d"),
            "total_price": 180000.00,  # 5 days * 36000
            "status": "returned",
            "created_at": now - timedelta(days=22),
        },
        {
            "user_id": bob_id,
            "product_id": product_ids[5],  # Epson EB-W52
            "start_date": (now - timedelta(days=12)).strftime("%Y-%m-%d"),
            "end_date":   (now - timedelta(days=8)).strftime("%Y-%m-%d"),
            "total_price": 21600.00,  # 4 days * 5400
            "status": "returned",
            "created_at": now - timedelta(days=14),
        },
        {
            "user_id": alice_id,
            "product_id": product_ids[13],  # Optoma ZH606
            "start_date": (now - timedelta(days=3)).strftime("%Y-%m-%d"),
            "end_date":   (now + timedelta(days=4)).strftime("%Y-%m-%d"),
            "total_price": 231000.00,  # 7 days * 33000
            "status": "active",
            "created_at": now - timedelta(days=5),
        },
        {
            "user_id": bob_id,
            "product_id": product_ids[12],  # Barco DP2K-10S
            "start_date": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date":   (now + timedelta(days=5)).strftime("%Y-%m-%d"),
            "total_price": 630000.00,  # 6 days * 105000
            "status": "active",
            "created_at": now - timedelta(days=2),
        },
        {
            "user_id": alice_id,
            "product_id": product_ids[9],  # Samsung The Premiere LSP9T
            "start_date": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
            "end_date":   (now + timedelta(days=8)).strftime("%Y-%m-%d"),
            "total_price": 135000.00,  # 3 days * 45000
            "status": "pending",
            "created_at": now - timedelta(hours=5),
        },
    ]

    result = db["rentals"].insert_many(rentals)
    print(f"[seed] Inserted {len(result.inserted_ids)} rentals.")
    return result.inserted_ids


if __name__ == "__main__":
    drop_all()
    create_indexes()
    user_ids    = seed_users()
    cat_ids     = seed_categories()
    product_ids = seed_products(cat_ids)
    seed_orders(user_ids, product_ids)
    seed_rentals(user_ids, product_ids)
    print("\n[seed] Done! All 6 collections seeded.")
    print("Credentials (3 Distinct Roles):")
    print("  Admin (Full Control)     : admin@projectorshop.com / ProjAdmin#2026!Secure")
    print("  Staff (Operations/Rentals): staff@projectorshop.com / ProjStaff#2026!Secure")
    print("  Customer 1 (Client)      : alice@example.com       / Alice#Pass2026$")
    print("  Customer 2 (Client)      : bob@example.com         / Bob#ProjStore99*")