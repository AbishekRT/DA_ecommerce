"""
seed.py
Seeds the MongoDB database with at least 15 documents per each collection:
  - 15 product categories
  - 20 projector products with realistic specs
  - 16 users (admins, staff, customers)
  - 15 active user carts
  - 18 realistic purchase orders
  - 18 realistic rental reservations

Also creates all required indexes explicitly.

Run with:  python seed.py
"""

from datetime import datetime, timezone, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

try:
    import certifi
    ca = certifi.where()
except Exception:
    ca = None

load_dotenv()

mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
client_kwargs = {
    "serverSelectionTimeoutMS": 5000,
    "connectTimeoutMS": 5000,
}
if "mongodb+srv://" in mongo_uri and ca:
    client_kwargs["tlsCAFile"] = ca

client = MongoClient(mongo_uri, **client_kwargs)
db     = client[os.getenv("DATABASE_NAME", "projector_ecommerce")]


def drop_all():
    """Drop all collections for a clean seed."""
    for col in ["users", "categories", "products", "carts", "orders", "rentals"]:
        db[col].drop()
    print("[seed] Dropped all collections.")


def create_indexes():
    """
    Create all indexes explicitly.
    """
    db["users"].create_index([("email", ASCENDING)], unique=True)
    db["products"].create_index([("category_id", ASCENDING)])
    db["products"].create_index([("type", ASCENDING)])
    db["products"].create_index([("name", "text"), ("brand", "text"), ("description", "text")])
    db["rentals"].create_index([
        ("product_id", ASCENDING),
        ("start_date",  ASCENDING),
        ("end_date",    ASCENDING),
    ])
    db["orders"].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    print("[seed] Indexes created.")


def seed_users():
    now = datetime.now(timezone.utc)
    users = [
        # Admins & Staff
        {
            "email":         "admin@projectorshop.com",
            "password_hash": generate_password_hash("ProjAdmin#2026!Secure"),
            "name":          "Abishek Shanaka (Lead Admin)",
            "role":          "admin",
            "phone":         "+94 77 123 4567",
            "address":       "123 Galle Road, Colombo 03, Sri Lanka",
            "created_at":    now - timedelta(days=90),
        },
        {
            "email":         "techops@projectorshop.com",
            "password_hash": generate_password_hash("TechOps#2026!Master"),
            "name":          "Marcus Vance (Infrastructure Admin)",
            "role":          "admin",
            "phone":         "+94 71 987 6543",
            "address":       "45 Kandy Road, Kiribathgoda, Sri Lanka",
            "created_at":    now - timedelta(days=85),
        },
        {
            "email":         "staff@projectorshop.com",
            "password_hash": generate_password_hash("ProjStaff#2026!Secure"),
            "name":          "Sarah Perera (Rental Fleet Manager)",
            "role":          "staff",
            "phone":         "+94 76 234 5678",
            "address":       "12 Station Road, Bambalapitiya, Colombo",
            "created_at":    now - timedelta(days=75),
        },
        {
            "email":         "logistics@projectorshop.com",
            "password_hash": generate_password_hash("Logistics#2026!Secure"),
            "name":          "Kasun Jayawardena (Fulfillment Staff)",
            "role":          "staff",
            "phone":         "+94 75 345 6789",
            "address":       "88 Negombo Road, Wattala, Sri Lanka",
            "created_at":    now - timedelta(days=70),
        },
        # Customers
        {
            "email":         "alice@example.com",
            "password_hash": generate_password_hash("Alice#Pass2026$"),
            "name":          "Alice Johnson",
            "role":          "customer",
            "phone":         "+94 77 334 1122",
            "address":       "14 Albert Crescent, Colombo 07",
            "created_at":    now - timedelta(days=60),
        },
        {
            "email":         "bob@example.com",
            "password_hash": generate_password_hash("Bob#ProjStore99*"),
            "name":          "Bob Smith",
            "role":          "customer",
            "phone":         "+94 70 445 2233",
            "address":       "89 Duplication Road, Kollupitiya",
            "created_at":    now - timedelta(days=55),
        },
        {
            "email":         "charlie.d@gmail.com",
            "password_hash": generate_password_hash("Charlie#2026!Pass"),
            "name":          "Charlie Davis",
            "role":          "customer",
            "phone":         "+94 72 556 3344",
            "address":       "23 High Level Road, Nugegoda",
            "created_at":    now - timedelta(days=50),
        },
        {
            "email":         "dilani.fernando@outlook.com",
            "password_hash": generate_password_hash("Dilani#2026!Secure"),
            "name":          "Dilani Fernando",
            "role":          "customer",
            "phone":         "+94 78 667 4455",
            "address":       "55 Templers Road, Mount Lavinia",
            "created_at":    now - timedelta(days=45),
        },
        {
            "email":         "evan.wright@yahoo.com",
            "password_hash": generate_password_hash("Evan#Proj2026!"),
            "name":          "Evan Wright",
            "role":          "customer",
            "phone":         "+94 77 778 5566",
            "address":       "71 Parliament Road, Kotte",
            "created_at":    now - timedelta(days=40),
        },
        {
            "email":         "fatima.rizvi@gmail.com",
            "password_hash": generate_password_hash("Fatima#2026!Pass"),
            "name":          "Fatima Rizvi",
            "role":          "customer",
            "phone":         "+94 71 889 6677",
            "address":       "102 Baseline Road, Dematagoda",
            "created_at":    now - timedelta(days=35),
        },
        {
            "email":         "gayan.wijesinghe@gmail.com",
            "password_hash": generate_password_hash("Gayan#2026!Secure"),
            "name":          "Gayan Wijesinghe",
            "role":          "customer",
            "phone":         "+94 76 990 7788",
            "address":       "34 Nawala Road, Rajagiriya",
            "created_at":    now - timedelta(days=30),
        },
        {
            "email":         "hannah.clark@company.com",
            "password_hash": generate_password_hash("Hannah#2026!Pass"),
            "name":          "Hannah Clark",
            "role":          "customer",
            "phone":         "+94 75 112 8899",
            "address":       "67 Havelock Road, Colombo 05",
            "created_at":    now - timedelta(days=25),
        },
        {
            "email":         "ishan.madushanka@gmail.com",
            "password_hash": generate_password_hash("Ishan#2026!Secure"),
            "name":          "Ishan Madushanka",
            "role":          "customer",
            "phone":         "+94 77 223 9900",
            "address":       "92 Cotta Road, Borella",
            "created_at":    now - timedelta(days=20),
        },
        {
            "email":         "jessica.m@creative.io",
            "password_hash": generate_password_hash("Jessica#2026!Pass"),
            "name":          "Jessica Miller",
            "role":          "customer",
            "phone":         "+94 70 334 0011",
            "address":       "18 Horton Place, Colombo 07",
            "created_at":    now - timedelta(days=15),
        },
        {
            "email":         "kamal.de.silva@live.com",
            "password_hash": generate_password_hash("Kamal#2026!Pass"),
            "name":          "Kamal De Silva",
            "role":          "customer",
            "phone":         "+94 72 445 1122",
            "address":       "44 Galle Face Court, Colombo 03",
            "created_at":    now - timedelta(days=10),
        },
        {
            "email":         "laura.adams@events.lk",
            "password_hash": generate_password_hash("Laura#2026!Secure"),
            "name":          "Laura Adams",
            "role":          "customer",
            "phone":         "+94 78 556 2233",
            "address":       "300 Union Place, Colombo 02",
            "created_at":    now - timedelta(days=5),
        },
    ]
    result = db["users"].insert_many(users)
    print(f"[seed] Inserted {len(result.inserted_ids)} users.")
    return result.inserted_ids


def seed_categories():
    categories = [
        {"name": "Home Cinema",              "description": "High-brightness projectors engineered for immersive home theatre entertainment."},
        {"name": "Business & Portable",      "description": "Compact, lightweight projectors with crisp text for meetings, travel, and classrooms."},
        {"name": "4K Ultra HD",              "description": "True 4K UHD resolution projectors delivering ultra-fine clarity and HDR dynamic range."},
        {"name": "Ultra Short Throw",        "description": "Laser TV projectors projecting massive 120-inch displays from just inches away."},
        {"name": "Outdoor & Large Venue",    "description": "High-lumen heavy-duty projectors built for concerts, church sanctuaries, and outdoor cinemas."},
        {"name": "Gaming Projectors",        "description": "Low-input-lag projectors with 240Hz refresh rates for fast-paced competitive gaming."},
        {"name": "Laser Phosphor",           "description": "Maintenance-free solid-state laser light source systems with 25,000+ hours lifespan."},
        {"name": "Pico & Pocket Mini",       "description": "Ultra-portable battery-powered projectors that fit right inside your backpack or pocket."},
        {"name": "Interactive Education",    "description": "Touch and smart-pen enabled projectors designed for interactive classrooms and boardrooms."},
        {"name": "Ceiling & Fixed Install",  "description": "High-throw precision motorized lens shift systems for permanent auditoriums."},
        {"name": "ALR Projector Screens",    "description": "Ambient Light Rejecting fixed-frame and motorized tensioned projection screens."},
        {"name": "Projector Mounts & Lifts", "description": "Heavy-duty motorized ceiling drop lifts and universal micro-adjustable mounts."},
        {"name": "Wireless HDMI & Dongles",  "description": "Zero-latency 4K wireless video transmitters and AirPlay / Miracast receivers."},
        {"name": "Surround Sound Audio",     "description": "Dolby Atmos soundbars and high-fidelity AV receiver packages tailored for projectors."},
        {"name": "Lamps & Maintenance",      "description": "Original OEM replacement bulbs, air filtration units, and optic cleaning kits."},
    ]
    result = db["categories"].insert_many(categories)
    print(f"[seed] Inserted {len(result.inserted_ids)} categories.")
    return result.inserted_ids


def seed_products(cat_ids):
    c_home, c_biz, c_4k, c_ust, c_outdoor, c_game, c_laser, c_pico, c_edu, c_ceil, c_screen, c_mount, c_wifi, c_audio, c_lamp = cat_ids
    now = datetime.now(timezone.utc)

    real_images = [
        "/static/images/products/03_fe08a650-da17-4def-9ccf-70a64b25ee7f.webp",
        "/static/images/products/1_1_2bdf3d70-f93d-4845-99f6-a827185f250e.webp",
        "/static/images/products/1_2540cf6e-1822-4368-b1f6-7eb5f3da4e16.webp",
        "/static/images/products/20260509104552.webp",
        "/static/images/products/3034a1133efe01daba919094b70c6310.webp",
        "/static/images/products/489651320.webp",
        "/static/images/products/b8421501ceee8ed8defa49d79fc692df.webp",
        "/static/images/products/S2f98a53d4fa749ee94613590a788b641u.webp",
        "/static/images/products/S2fb390a462704106ab1184a568a9195b5_256a857e-79e2-4907-b2b0-03ea051fcebf.webp",
        "/static/images/products/S49e23f3ef07c48478e72fa336f1097daY.webp",
        "/static/images/products/Sbb001356f372499f8252b51a936aed97G.webp",
    ]

    products = [
        # 1. Home Cinema
        {
            "name": "Epson Home Cinema 2350",
            "brand": "Epson",
            "category_id": c_home,
            "type": "both",
            "sale_price": 389900.00,
            "rent_price_per_day": 13500.00,
            "stock_qty": 8,
            "image_url": real_images[0],
            "description": "Full HD 3LCD smart home cinema projector with 4500 lumens. Ideal for dedicated home theatre rooms and bright living spaces.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 4500,
                "throw_distance": "1.0m - 5.5m",
                "connectivity": ["HDMI", "USB", "WiFi", "Bluetooth"],
            },
            "created_at": now - timedelta(days=60),
        },
        # 2. BenQ HT3550i
        {
            "name": "BenQ HT3550i CinematicColor",
            "brand": "BenQ",
            "category_id": c_4k,
            "type": "sell",
            "sale_price": 509900.00,
            "rent_price_per_day": None,
            "stock_qty": 5,
            "image_url": real_images[1],
            "description": "True 4K HDR DLP home projector with factory-calibrated DCI-P3 wide color gamut and integrated Android TV.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2000,
                "throw_distance": "1.2m - 7.2m",
                "connectivity": ["HDMI 2.0", "USB", "Android TV"],
            },
            "created_at": now - timedelta(days=58),
        },
        # 3. Sony VPL-VW325ES
        {
            "name": "Sony VPL-VW325ES Native 4K",
            "brand": "Sony",
            "category_id": c_home,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 36000.00,
            "stock_qty": 3,
            "image_url": real_images[2],
            "description": "Ultra-high-end Sony native 4K SXRD cinema projector powered by the X1 processor for unrivaled HDR mastering. Rental exclusive.",
            "specs": {
                "resolution": "4096x2160 (Native 4K)",
                "brightness_lumens": 1500,
                "throw_distance": "1.5m - 8.0m",
                "connectivity": ["HDMI 2.0b", "RS-232C", "IR Input"],
            },
            "created_at": now - timedelta(days=55),
        },
        # 4. Anker Nebula Capsule 3
        {
            "name": "Anker Nebula Capsule 3 Laser",
            "brand": "Anker",
            "category_id": c_pico,
            "type": "both",
            "sale_price": 179900.00,
            "rent_price_per_day": 6000.00,
            "stock_qty": 12,
            "image_url": real_images[3],
            "description": "Pocket-sized laser mini projector the size of a soda can. Built-in battery, autofocus, and Google TV onboard.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 300,
                "throw_distance": "0.8m - 3.5m",
                "connectivity": ["HDMI", "USB-C", "WiFi", "Bluetooth", "Google TV"],
            },
            "created_at": now - timedelta(days=50),
        },
        # 5. Optoma ML1080ST
        {
            "name": "Optoma ML1080ST Short Throw Laser",
            "brand": "Optoma",
            "category_id": c_biz,
            "type": "both",
            "sale_price": 269900.00,
            "rent_price_per_day": 9000.00,
            "stock_qty": 9,
            "image_url": real_images[4],
            "description": "Ultra-compact RGB triple laser projector weighing just 0.9 kg with short-throw lens and USB-C power delivery.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 1200,
                "throw_distance": "0.7m - 4.0m",
                "connectivity": ["HDMI", "USB-A", "USB-C DP"],
            },
            "created_at": now - timedelta(days=48),
        },
        # 6. Epson EB-W52
        {
            "name": "Epson EB-W52 Presentation Projector",
            "brand": "Epson",
            "category_id": c_biz,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 5400.00,
            "stock_qty": 15,
            "image_url": real_images[5],
            "description": "Workhorse WXGA business presentation projector with 4000 lumens output. Perfect for corporate workshops and classrooms.",
            "specs": {
                "resolution": "1280x800 (WXGA)",
                "brightness_lumens": 4000,
                "throw_distance": "0.9m - 12.3m",
                "connectivity": ["HDMI", "VGA", "USB", "LAN"],
            },
            "created_at": now - timedelta(days=45),
        },
        # 7. LG CineBeam HU85LA
        {
            "name": "LG CineBeam HU85LA 4K UST Laser",
            "brand": "LG",
            "category_id": c_ust,
            "type": "both",
            "sale_price": 899900.00,
            "rent_price_per_day": 28000.00,
            "stock_qty": 4,
            "image_url": real_images[6],
            "description": "Flagship 4K UHD triple laser ultra-short throw projector delivering a 120-inch frame from only 7.2 inches away.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 4000,
                "throw_distance": "0.12m - 0.4m",
                "connectivity": ["HDMI 2.0", "USB", "WiFi", "Bluetooth", "webOS"],
            },
            "created_at": now - timedelta(days=42),
        },
        # 8. Formovie Theater 4K
        {
            "name": "Formovie Theater 4K Laser TV",
            "brand": "Formovie",
            "category_id": c_ust,
            "type": "sell",
            "sale_price": 949900.00,
            "rent_price_per_day": None,
            "stock_qty": 4,
            "image_url": real_images[7],
            "description": "Triple-laser ALPD 4.0 ultra-short throw projector with Dolby Vision and Bowers & Wilkins acoustics tuned to perfection.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2800,
                "throw_distance": "0.14m - 0.5m",
                "connectivity": ["HDMI 2.1 eARC", "USB", "Android TV 11"],
            },
            "created_at": now - timedelta(days=40),
        },
        # 9. Samsung The Premiere LSP9T
        {
            "name": "Samsung The Premiere LSP9T Triple Laser",
            "brand": "Samsung",
            "category_id": c_ust,
            "type": "both",
            "sale_price": 1399900.00,
            "rent_price_per_day": 45000.00,
            "stock_qty": 3,
            "image_url": real_images[8],
            "description": "The world's first HDR10+ certified triple laser projector with 40W 4.2ch built-in Acoustic Beam sound system.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2800,
                "throw_distance": "0.11m - 0.38m",
                "connectivity": ["HDMI 2.0b", "eARC", "Optical Out", "Tizen OS"],
            },
            "created_at": now - timedelta(days=38),
        },
        # 10. BenQ TK700STi Gaming
        {
            "name": "BenQ TK700STi 4K Gaming Projector",
            "brand": "BenQ",
            "category_id": c_game,
            "type": "both",
            "sale_price": 469900.00,
            "rent_price_per_day": 14000.00,
            "stock_qty": 7,
            "image_url": real_images[9],
            "description": "Ultra-low 16ms 4K/60Hz and 4ms 1080p/240Hz input lag gaming projector with tailored Game Sound and FPS presets.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 3000,
                "throw_distance": "1.0m - 5.0m",
                "connectivity": ["HDMI 2.0 (Dual)", "eARC", "Android TV"],
            },
            "created_at": now - timedelta(days=35),
        },
        # 11. ViewSonic PX701-4K Gaming
        {
            "name": "ViewSonic PX701-4K High Refresh",
            "brand": "ViewSonic",
            "category_id": c_game,
            "type": "sell",
            "sale_price": 319900.00,
            "rent_price_per_day": None,
            "stock_qty": 11,
            "image_url": real_images[10],
            "description": "3200 ANSI Lumens 4K gaming powerhouse with 4.2ms ultra-fast response and 240Hz refresh rate.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 3200,
                "throw_distance": "1.0m - 6.0m",
                "connectivity": ["Dual HDMI 2.0", "USB Power", "Audio Out"],
            },
            "created_at": now - timedelta(days=32),
        },
        # 12. Christie Crimson HD31
        {
            "name": "Christie Crimson HD31 Venue Master",
            "brand": "Christie",
            "category_id": c_outdoor,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 85000.00,
            "stock_qty": 2,
            "image_url": real_images[0],
            "description": "31,500 ISO lumen 3DLP laser phosphor projector engineered for concert tours, stadium mapping, and massive open-air screenings.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 31500,
                "throw_distance": "3.0m - 30.0m",
                "connectivity": ["3G-SDI", "HDMI 2.0", "HDBaseT", "DisplayPort"],
            },
            "created_at": now - timedelta(days=30),
        },
        # 13. Barco DP2K-10S
        {
            "name": "Barco DP2K-10S Cinema Fleet",
            "brand": "Barco",
            "category_id": c_outdoor,
            "type": "rent",
            "sale_price": None,
            "rent_price_per_day": 105000.00,
            "stock_qty": 2,
            "image_url": real_images[1],
            "description": "DCI-compliant digital commercial cinema projector with integrated Alchemy server. The standard for film festivals and outdoor premieres.",
            "specs": {
                "resolution": "2048x1080 (2K Cinema)",
                "brightness_lumens": 10000,
                "throw_distance": "5.0m - 25.0m",
                "connectivity": ["Dual HD-SDI", "HDMI 1.4a", "Gigabit Ethernet"],
            },
            "created_at": now - timedelta(days=28),
        },
        # 14. Optoma ZH606 Laser
        {
            "name": "Optoma ZH606 Professional Laser",
            "brand": "Optoma",
            "category_id": c_laser,
            "type": "both",
            "sale_price": 729900.00,
            "rent_price_per_day": 33000.00,
            "stock_qty": 6,
            "image_url": real_images[2],
            "description": "6,000 lumen compact DuraCore laser projector engineered for 24/7 maintenance-free continuous operation.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 6000,
                "throw_distance": "1.3m - 9.4m",
                "connectivity": ["HDMI 2.0", "HDBaseT", "VGA", "RS232"],
            },
            "created_at": now - timedelta(days=25),
        },
        # 15. Epson Pro EX9240
        {
            "name": "Epson Pro EX9240 Wireless",
            "brand": "Epson",
            "category_id": c_biz,
            "type": "sell",
            "sale_price": 289900.00,
            "rent_price_per_day": None,
            "stock_qty": 14,
            "image_url": real_images[3],
            "description": "Full HD 1080p dynamic wireless projector with 4000 lumens of equal color and white brightness.",
            "specs": {
                "resolution": "1920x1080 (Full HD)",
                "brightness_lumens": 4000,
                "throw_distance": "1.1m - 9.0m",
                "connectivity": ["Dual HDMI", "USB", "Miracast", "WiFi"],
            },
            "created_at": now - timedelta(days=22),
        },
        # 16. Epson Pro Cinema LS12000B
        {
            "name": "Epson Pro Cinema LS12000B Laser",
            "brand": "Epson",
            "category_id": c_4k,
            "type": "both",
            "sale_price": 1499900.00,
            "rent_price_per_day": 19000.00,
            "stock_qty": 2,
            "image_url": real_images[4],
            "description": "Epson flagship 4K 120Hz laser projector with 2700 lumens, motorized optics, and advanced HDR10+ frame interpolation.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2700,
                "throw_distance": "1.3m - 8.7m",
                "connectivity": ["Dual HDMI 2.1 (40Gbps)", "USB", "LAN", "RS-232C"],
            },
            "created_at": now - timedelta(days=20),
        },
        # 17. ViewSonic X100-4K+
        {
            "name": "ViewSonic X100-4K+ Home Theatre",
            "brand": "ViewSonic",
            "category_id": c_4k,
            "type": "both",
            "sale_price": 539900.00,
            "rent_price_per_day": 18000.00,
            "stock_qty": 5,
            "image_url": real_images[5],
            "description": "4K 2nd generation LED projector with built-in Harman Kardon acoustics, ultra-quiet cooling, and wide lens shift.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2900,
                "throw_distance": "1.5m - 8.5m",
                "connectivity": ["Quad HDMI 2.0", "USB", "WiFi", "Bluetooth", "Harman Kardon"],
            },
            "created_at": now - timedelta(days=18),
        },
        # 18. XGIMI Horizon Ultra 4K
        {
            "name": "XGIMI Horizon Ultra Dual Light 4K",
            "brand": "XGIMI",
            "category_id": c_home,
            "type": "both",
            "sale_price": 1179900.00,
            "rent_price_per_day": 15000.00,
            "stock_qty": 6,
            "image_url": real_images[6],
            "description": "The world's first 4K long-throw projector with Dolby Vision combining Laser and LED Dual Light technology.",
            "specs": {
                "resolution": "3840x2160 (4K UHD)",
                "brightness_lumens": 2300,
                "throw_distance": "1.4m - 8.0m",
                "connectivity": ["HDMI 2.0 (eARC)", "USB", "WiFi 6", "Bluetooth 5.2", "Android TV 11"],
            },
            "created_at": now - timedelta(days=15),
        },
        # 19. Elite Screens CineGrey 120" ALR Screen
        {
            "name": "Elite Screens Aeon CineGrey 120\" ALR",
            "brand": "Elite Screens",
            "category_id": c_screen,
            "type": "sell",
            "sale_price": 249900.00,
            "rent_price_per_day": None,
            "stock_qty": 8,
            "image_url": real_images[7],
            "description": "Edge Free 120-inch 16:9 ambient light rejecting fixed frame screen designed specifically for 4K/8K projectors.",
            "specs": {
                "screen_size": "120 inch diagonal",
                "aspect_ratio": "16:9",
                "gain": "1.5 High Contrast",
                "viewing_angle": "160 degrees",
            },
            "created_at": now - timedelta(days=12),
        },
        # 20. Chief Universal Micro-Adjust Ceiling Mount
        {
            "name": "Chief RPA Elite Universal Mount",
            "brand": "Chief",
            "category_id": c_mount,
            "type": "both",
            "sale_price": 65900.00,
            "rent_price_per_day": 3500.00,
            "stock_qty": 20,
            "image_url": real_images[8],
            "description": "Engineered micro-adjustable ceiling bracket system with integrated cable management and Centris technology.",
            "specs": {
                "max_weight_capacity": "22.7 kg",
                "pitch_adjustment": "+/- 20 degrees",
                "roll_adjustment": "+/- 3 degrees",
                "yaw_adjustment": "360 degrees",
            },
            "created_at": now - timedelta(days=10),
        },
    ]
    result = db["products"].insert_many(products)
    print(f"[seed] Inserted {len(result.inserted_ids)} products.")
    return result.inserted_ids


def seed_carts(user_ids, product_ids):
    """
    Seed 15 active shopping carts with realistic items.
    """
    now = datetime.now(timezone.utc)
    carts = []
    # Create carts for customers (index 4 to 15) and others
    for idx in range(15):
        uid = user_ids[idx + 1] if idx + 1 < len(user_ids) else user_ids[0]
        p1 = product_ids[idx % len(product_ids)]
        p2 = product_ids[(idx + 3) % len(product_ids)]
        
        items = [
            {
                "product_id": p1,
                "type": "sell",
                "qty": 1 + (idx % 2),
            },
            {
                "product_id": p2,
                "type": "rent",
                "qty": 1,
                "rent_start_date": now + timedelta(days=idx + 2),
                "rent_end_date": now + timedelta(days=idx + 6),
            }
        ]
        carts.append({
            "user_id": uid,
            "items": items,
            "updated_at": now - timedelta(hours=idx * 3 + 1),
        })

    result = db["carts"].insert_many(carts)
    print(f"[seed] Inserted {len(result.inserted_ids)} active carts.")
    return result.inserted_ids


def seed_orders(user_ids, product_ids):
    """
    Seed 18 realistic purchase orders across different customers, statuses, and dates.
    """
    now = datetime.now(timezone.utc)
    statuses = ["completed", "completed", "shipped", "confirmed", "processing", "pending"]
    orders = []

    order_configs = [
        (4, [0], 389900.00, 30, "completed"),
        (5, [3, 1], 689800.00, 27, "completed"),
        (6, [6], 899900.00, 25, "completed"),
        (7, [16], 539900.00, 22, "completed"),
        (8, [9], 469900.00, 20, "shipped"),
        (9, [14], 289900.00, 18, "shipped"),
        (10, [18], 249900.00, 15, "shipped"),
        (11, [7], 949900.00, 14, "confirmed"),
        (12, [17], 1179900.00, 12, "confirmed"),
        (13, [10, 19], 385800.00, 10, "processing"),
        (14, [0, 19], 455800.00, 8, "processing"),
        (15, [4], 269900.00, 7, "processing"),
        (4, [15], 1499900.00, 6, "confirmed"),
        (5, [8], 1399900.00, 5, "confirmed"),
        (6, [10], 319900.00, 4, "pending"),
        (7, [3, 19], 245800.00, 3, "pending"),
        (8, [1], 509900.00, 2, "pending"),
        (9, [18, 19], 315800.00, 1, "pending"),
    ]

    for uid_idx, p_indices, _unused_amt, days_ago, status in order_configs:
        uid = user_ids[uid_idx] if uid_idx < len(user_ids) else user_ids[4]
        items = []
        for p_idx in p_indices:
            p = db["products"].find_one({"_id": product_ids[p_idx]})
            price = p["sale_price"] if p and p.get("sale_price") else 250000.00
            name = p["name"] if p else f"Product #{p_idx}"
            items.append({
                "product_id": product_ids[p_idx],
                "name": name,
                "qty": 1,
                "unit_price": price,
                "subtotal": price,
            })
        order_total = sum(item["subtotal"] for item in items)
        orders.append({
            "user_id": uid,
            "items": items,
            "total": order_total,
            "status": status,
            "stock_deducted": False,
            "created_at": now - timedelta(days=days_ago),
        })

    result = db["orders"].insert_many(orders)
    print(f"[seed] Inserted {len(result.inserted_ids)} orders.")
    return result.inserted_ids


def seed_rentals(user_ids, product_ids):
    """
    Seed 18 realistic rental bookings across various customers, dates, and statuses.
    """
    now = datetime.now(timezone.utc)
    rentals = []

    rental_configs = [
        # (user_idx, prod_idx, start_delta, end_delta, total_price, status)
        (4, 2, -30, -25, 180000.00, "returned"),
        (5, 5, -28, -24, 21600.00, "returned"),
        (6, 11, -25, -20, 425000.00, "returned"),
        (7, 12, -22, -18, 420000.00, "returned"),
        (8, 0, -18, -14, 54000.00, "returned"),
        (9, 3, -15, -10, 30000.00, "returned"),
        (10, 13, -10, -5, 165000.00, "returned"),
        (11, 4, -8, -4, 36000.00, "returned"),
        (12, 13, -3, 4, 231000.00, "active"),
        (13, 12, -2, 4, 630000.00, "active"),
        (14, 2, -1, 5, 216000.00, "active"),
        (15, 6, -1, 3, 112000.00, "active"),
        (4, 8, 2, 6, 180000.00, "reserved"),
        (5, 15, 3, 7, 76000.00, "reserved"),
        (6, 17, 4, 8, 60000.00, "reserved"),
        (7, 9, 5, 8, 135000.00, "pending"),
        (8, 0, 6, 10, 54000.00, "pending"),
        (9, 16, 7, 11, 72000.00, "pending"),
    ]

    for uid_idx, p_idx, s_delta, e_delta, total_amt, status in rental_configs:
        uid = user_ids[uid_idx] if uid_idx < len(user_ids) else user_ids[4]
        rentals.append({
            "user_id": uid,
            "product_id": product_ids[p_idx],
            "start_date": (now + timedelta(days=s_delta)).strftime("%Y-%m-%d"),
            "end_date":   (now + timedelta(days=e_delta)).strftime("%Y-%m-%d"),
            "total_price": total_amt,
            "status": status,
            "created_at": now + timedelta(days=s_delta - 2),
        })

    result = db["rentals"].insert_many(rentals)
    print(f"[seed] Inserted {len(result.inserted_ids)} rentals.")
    return result.inserted_ids


if __name__ == "__main__":
    drop_all()
    create_indexes()
    user_ids    = seed_users()
    cat_ids     = seed_categories()
    product_ids = seed_products(cat_ids)
    seed_carts(user_ids, product_ids)
    seed_orders(user_ids, product_ids)
    seed_rentals(user_ids, product_ids)
    print("\n[seed] SUCCESS! Seeded 15+ documents across all 6 collections.")
    print("Database Counts:")
    for col in ["categories", "products", "users", "carts", "orders", "rentals"]:
        print(f"  - {col}: {db[col].count_documents({})} documents")