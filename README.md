# Projector Shop - E-Commerce Platform

A Flask + MongoDB e-commerce application for selling and renting projectors.
Built for academic demonstration of raw PyMongo usage (no ODM).

---

## Prerequisites

- Python 3.11+
- MongoDB Community Server running locally on port 27017
- MongoDB Compass (optional, for visual inspection)

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
The `.env` file is already included with defaults for local development:
```
MONGODB_URI=mongodb://localhost:27017/
SECRET_KEY=supersecretkey_change_in_production_2024
DATABASE_NAME=projector_ecommerce
```

### 3. Start MongoDB
Make sure your local MongoDB instance is running:
```bash
# Windows (if installed as a service):
net start MongoDB

# Or start manually:
mongod --dbpath C:/data/db
```

### 4. Seed the database
```bash
python seed.py
```
This creates all indexes, inserts sample data, and prints the login credentials.

**Default credentials (3 Distinct Roles):**
| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@projectorshop.com` | `ProjAdmin#2026!Secure` | Full System Control, Analytics & Financials |
| **Staff** | `staff@projectorshop.com` | `ProjStaff#2026!Secure` | Rental Operations, Inventory & Order Management |
| **Customer 1** | `alice@example.com` | `Alice#Pass2026$` | Storefront, Cart, Checkout, Order History |
| **Customer 2** | `bob@example.com` | `Bob#ProjStore99*` | Storefront, Cart, Checkout, Order History |

### 5. Run the Flask app
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Connecting MongoDB Compass

1. Open **MongoDB Compass**.
2. In the connection string field, enter: `mongodb://localhost:27017/`
3. Click **Connect**.
4. Select the **`projector_ecommerce`** database.
5. You can browse all 6 collections: `users`, `categories`, `products`, `carts`, `orders`, `rentals`.
6. Use the **Aggregations** tab in Compass to run and visualise the pipelines from `admin/routes.py`.

---

## Project Structure

```
projector_ecommerce/
├── app.py              # App factory, blueprint registration, user_loader
├── extensions.py       # MongoClient, collection handles, Flask-Login setup
├── models.py           # Thin User wrapper for Flask-Login (not an ODM)
├── auth/
│   ├── routes.py       # /register, /login, /logout
│   └── decorators.py   # @role_required("admin") decorator
├── customer/
│   └── routes.py       # Catalog, product detail, compare, cart, checkout, history
├── admin/
│   └── routes.py       # Product CRUD, order/rental management, aggregations
├── templates/          # Jinja2 templates (Bootstrap 5 via CDN)
├── static/css/         # Minimal custom CSS
├── seed.py             # Seeds database and creates indexes
├── .env                # Environment variables (not committed in production)
└── requirements.txt
```

---

## MongoDB Design Decisions

### Embedding vs Referencing

| Field / Document       | Decision  | Reason |
|------------------------|-----------|--------|
| `products.specs`       | **Embed** | Always accessed with the product; bounded size; never queried independently |
| `orders.items`         | **Embed** | Frozen price snapshot at checkout; never updated independently after creation |
| `products.category_id` | **Reference** | Categories are shared across many products and managed independently |
| `carts.product_id`     | **Reference** | Cart must show live product price/stock, not a frozen snapshot |
| `rentals.product_id`   | **Reference** | Availability queries filter rentals by product — requires querying rentals independently |
| `orders.user_id`       | **Reference** | User data is shared and updated independently of orders |

### Indexes Created by seed.py

| Collection | Field(s)              | Type     | Purpose |
|------------|-----------------------|----------|---------|
| users      | email                 | Unique   | Fast login lookup, prevents duplicates |
| products   | category_id           | Standard | Catalog filter by category |
| products   | type                  | Standard | Catalog filter by type |
| rentals    | product_id + start_date + end_date | Compound | Availability conflict query |
| orders     | user_id               | Standard | Customer order history lookup |
| orders     | created_at (desc)     | Standard | Sort order history newest-first |

---

## Key MongoDB Queries for Viva

### 1. Availability conflict check (rentals)
```python
conflict = rentals_col.find_one({
    "product_id": product_id,
    "status": {"$in": ["confirmed", "active"]},
    "start_date": {"$lt": requested_end},
    "end_date":   {"$gt": requested_start},
})
```
Two date ranges [A,B] and [C,D] overlap when `A < D AND C < B`. Cancelled rentals are excluded by the status filter.

### 2. Revenue by category (aggregation)
See `admin/routes.py` -> `dashboard()` -> `revenue_pipeline`. Steps: `$match` -> `$unwind` -> `$lookup` (products) -> `$lookup` (categories) -> `$group` -> `$sort`.

### 3. Rental utilisation (aggregation)
See `admin/routes.py` -> `dashboard()` -> `utilisation_pipeline`. Steps: `$match` -> `$group` (sum ms) -> `$lookup` -> `$project` (ms to days) -> `$sort`.

### 4. Product comparison
```python
products = products_col.find({"_id": {"$in": [oid1, oid2]}})
```
Simple `$in` on two ObjectIds — single round-trip, no join needed.

### 5. Conditional customer cancel
```python
orders_col.update_one(
    {"_id": order_id, "user_id": user_id, "status": "pending"},
    {"$set": {"status": "cancelled"}}
)
```
Status check is inside the filter — atomic check-and-update.