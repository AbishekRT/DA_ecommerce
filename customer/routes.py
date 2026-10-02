"""
customer/routes.py
All customer-facing routes: catalog, product detail, compare,
cart management, checkout, and order history.

Every MongoDB operation is a direct, explicit PyMongo call.
No ODM, no repository layer — every query is readable in-place.
"""

from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort, session
)
from flask_login import login_required, current_user

from extensions import (
    products_col, categories_col, carts_col,
    orders_col, rentals_col
)

customer_bp = Blueprint("customer", __name__, template_folder="../templates/customer")

# ---------------------------------------------------------------------------
# Sri Lanka Timezone (UTC+5:30) and Rental Date Validation Helpers
# ---------------------------------------------------------------------------
SL_TZ = timezone(timedelta(hours=5, minutes=30))

def get_sl_now():
    """Returns current datetime in Sri Lanka timezone."""
    return datetime.now(SL_TZ)

def get_sl_today():
    """Returns current date in Sri Lanka timezone."""
    return datetime.now(SL_TZ).date()

def validate_rental_dates(start_str, end_str):
    """
    Validates rental start and end date strings based on Sri Lanka business rules.
    Rules:
    1. Both start_date and end_date are required in YYYY-MM-DD format.
    2. start_date must not be in the past.
    3. end_date must be strictly after start_date (minimum 1 full day).
    4. Duration must be at most 30 days.
    Returns: (is_valid, error_message, start_utc, end_utc)
    """
    if not start_str or not end_str:
        return False, "Both start and end dates are required for rental bookings.", None, None
    try:
        start_d = datetime.strptime(str(start_str).strip(), "%Y-%m-%d").date()
        end_d   = datetime.strptime(str(end_str).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False, "Rental dates must be in valid YYYY-MM-DD format.", None, None

    today = get_sl_today()
    if start_d < today:
        return False, "Rental start date cannot be in the past.", None, None

    if end_d <= start_d:
        return False, "Rental end date must be strictly after start date (minimum 1 day).", None, None

    duration = (end_d - start_d).days
    if duration > 30:
        return False, f"Rental duration ({duration} days) exceeds the maximum allowed limit of 30 days.", None, None

    start_utc = datetime(start_d.year, start_d.month, start_d.day, tzinfo=timezone.utc)
    end_utc   = datetime(end_d.year, end_d.month, end_d.day, tzinfo=timezone.utc)
    return True, "", start_utc, end_utc


# ===========================================================================
# HELPER - safe ObjectId conversion
# ===========================================================================
def _oid(s):
    """Convert string to ObjectId, abort 404 on invalid format."""
    try:
        return ObjectId(s)
    except (InvalidId, TypeError):
        abort(404)


# ===========================================================================
# CATALOG
# ===========================================================================
@customer_bp.route("/")
@customer_bp.route("/catalog")
def catalog():
    """
    Lists all products with optional filters.
    PyMongo find() with a dynamic query dict — plain and explainable.
    """
    query = {}

    # Filter by category (referenced by ObjectId)
    cat_id = request.args.get("category")
    if cat_id:
        try:
            query["category_id"] = ObjectId(cat_id)
        except Exception:
            pass

    # Filter by type: "sell", "rent", or "both" means either
    type_filter = request.args.get("type")
    if type_filter in ("sell", "rent"):
        # $in matches products listed as that specific type OR as "both"
        query["type"] = {"$in": [type_filter, "both"]}

    # Filter by search query (text/regex matching name, brand, description, resolution)
    q = request.args.get("q", "").strip()
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"brand": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"specs.resolution": {"$regex": q, "$options": "i"}},
        ]

    # Direct PyMongo find — returns a cursor of product documents
    products = list(products_col.find(query))

    # Sort handling
    sort_by = request.args.get("sort", "featured")
    if sort_by == "price_low":
        products = sorted(products, key=lambda p: (p.get("sale_price") or p.get("rent_price_per_day") or 0))
    elif sort_by == "price_high":
        products = sorted(products, key=lambda p: (p.get("sale_price") or p.get("rent_price_per_day") or 0), reverse=True)
    elif sort_by == "name_asc":
        products = sorted(products, key=lambda p: p.get("name", "").lower())

    # Fetch all categories for the filter pills
    categories = list(categories_col.find())

    return render_template(
        "customer/catalog.html",
        products=products,
        categories=categories,
        selected_cat=cat_id,
        selected_type=type_filter,
        selected_sort=sort_by,
        search_query=q,
    )


# ===========================================================================
# PRODUCT DETAIL
# ===========================================================================
@customer_bp.route("/product/<product_id>")
def product_detail(product_id):
    """
    Fetches a single product by _id.
    specs is EMBEDDED in the product document — always retrieved together,
    never queried independently. No join / lookup needed.
    """
    # EMBED: specs is embedded inside the product document because it is
    # always accessed with the product, has a fixed/bounded size, and is
    # never queried or updated independently.
    product = products_col.find_one({"_id": _oid(product_id)})
    if not product:
        abort(404)

    # REFERENCE: category_id is a reference to categories collection.
    # We do a second find_one here to get the category name for display.
    # It is referenced (not embedded) because categories are shared across
    # many products and must be manageable independently.
    category = categories_col.find_one({"_id": product["category_id"]})
    sl_today = get_sl_today().strftime("%Y-%m-%d")

    return render_template(
        "customer/product_detail.html",
        product=product,
        category=category,
        sl_today=sl_today,
    )


# ===========================================================================
# PRODUCT COMPARISON
# ===========================================================================
@customer_bp.route("/compare")
def compare():
    """
    Side-by-side comparison of exactly 2 products.
    Uses a simple $in query on two _id values — purposely kept simple
    and explainable for the viva.
    """
    ids = request.args.getlist("ids")
    products = []

    if len(ids) == 2:
        try:
            oid_list = [ObjectId(i) for i in ids]
        except Exception:
            oid_list = []

        if oid_list:
            # $in operator matches documents whose _id is in the provided list.
            # This fetches both products in a single round-trip to MongoDB.
            products = list(products_col.find({"_id": {"$in": oid_list}}))

    # Fetch all products for the selection form
    all_products = list(products_col.find({}, {"name": 1, "brand": 1}))

    return render_template(
        "customer/compare.html",
        products=products,
        all_products=all_products,
        selected_ids=ids,
    )


# ===========================================================================
# CART
# ===========================================================================
@customer_bp.route("/cart")
@login_required
def view_cart():
    """
    Displays the current user's cart.
    Cart items REFERENCE product_id so prices always reflect live data.
    """
    if current_user.role in ['admin', 'staff']:
        flash("Shopping cart is reserved for Customer accounts. Staff and Admins manage operations via the Management Console.", "info")
        return redirect(url_for("admin.dashboard" if current_user.role == "admin" else "admin.rentals_list"))

    # REFERENCE: cart items store product_id as a reference (not embedded
    # product data) so the price and stock shown in the cart always reflect
    # the current state of the products collection.
    cart = carts_col.find_one({"user_id": ObjectId(current_user.id)})
    enriched_items = []
    cart_total = 0

    if cart:
        for item in cart.get("items", []):
            # For each cart item, fetch the live product document
            product = products_col.find_one({"_id": item["product_id"]})
            if product:
                if item["type"] == "sell":
                    unit_price = product.get("sale_price", 0) or 0
                    subtotal = unit_price * item["qty"]
                else:  # rent
                    start = item.get("rent_start_date")
                    end   = item.get("rent_end_date")
                    days  = (end - start).days if start and end else 0
                    days  = max(days, 1)
                    unit_price = product.get("rent_price_per_day", 0) or 0
                    subtotal   = unit_price * days * item["qty"]
                cart_total += subtotal
                enriched_items.append({
                    "product":  product,
                    "item":     item,
                    "subtotal": subtotal,
                    "days":     (end - start).days if item["type"] == "rent" and start and end else None,
                })

    return render_template(
        "customer/cart.html",
        enriched_items=enriched_items,
        cart_total=cart_total,
    )


@customer_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    """
    Adds an item to the cart (upserts the cart document).
    One cart document per user — upserted with update_one + $setOnInsert.
    """
    if current_user.role in ['admin', 'staff']:
        flash("Shopping cart is disabled for Administrative and Staff accounts.", "warning")
        return redirect(url_for("customer.catalog"))

    product_id = request.form.get("product_id")
    item_type  = request.form.get("type")       # "sell" or "rent"

    product = products_col.find_one({"_id": _oid(product_id)})
    if not product:
        abort(404)

    # Validate mode vs product type
    if item_type == "sell" and product.get("type") == "rent":
        flash("This product is available for rent only.", "warning")
        return redirect(url_for("customer.product_detail", product_id=product_id))
    if item_type == "rent" and product.get("type") == "sell":
        flash("This product is available for purchase only.", "warning")
        return redirect(url_for("customer.product_detail", product_id=product_id))

    # Quantity validation
    try:
        qty = int(request.form.get("qty", 1))
    except (ValueError, TypeError):
        flash("Quantity must be a valid integer.", "danger")
        return redirect(url_for("customer.product_detail", product_id=product_id))

    if qty < 1:
        flash("Quantity must be at least 1.", "warning")
        return redirect(url_for("customer.product_detail", product_id=product_id))

    if item_type == "sell":
        stock_avail = product.get("stock_qty", 0) or 0
        if stock_avail <= 0:
            flash(f"'{product['name']}' is currently out of stock.", "danger")
            return redirect(url_for("customer.product_detail", product_id=product_id))
        if qty > stock_avail:
            flash(f"Requested quantity ({qty}) exceeds available stock ({stock_avail}).", "warning")
            return redirect(url_for("customer.product_detail", product_id=product_id))

    new_item = {
        # REFERENCE: product_id is stored as a reference so the cart always
        # reflects live product data (current price, stock) rather than a
        # frozen snapshot. This contrasts with orders.items which embeds
        # a price snapshot at checkout time.
        "product_id": _oid(product_id),
        "type":       item_type,
        "qty":        qty,
    }

    if item_type == "rent":
        start_str = request.form.get("rent_start_date") or request.form.get("rental_start") or ""
        end_str   = request.form.get("rent_end_date") or request.form.get("rental_end") or ""
        is_valid, err_msg, start_dt, end_dt = validate_rental_dates(start_str, end_str)
        if not is_valid:
            flash(err_msg, "danger")
            return redirect(url_for("customer.product_detail", product_id=product_id))
        new_item["rent_start_date"] = start_dt
        new_item["rent_end_date"]   = end_dt

    user_oid = ObjectId(current_user.id)

    # Check if this product+type combo already exists in the cart
    existing_cart = carts_col.find_one({"user_id": user_oid})
    if existing_cart:
        # Check for duplicate item
        duplicate = any(
            str(i["product_id"]) == product_id and i["type"] == item_type
            for i in existing_cart.get("items", [])
        )
        if duplicate:
            flash("This item is already in your cart.", "warning")
            return redirect(url_for("customer.view_cart"))

    # $push appends the new item into the items array.
    # $setOnInsert creates the cart document if it doesn't exist yet (upsert).
    carts_col.update_one(
        {"user_id": user_oid},
        {
            "$push": {"items": new_item},
            "$set":  {"updated_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"user_id": user_oid},
        },
        upsert=True,
    )
    flash("Item added to cart.", "success")
    return redirect(url_for("customer.view_cart"))


@customer_bp.route("/cart/remove", methods=["POST"])
@login_required
def remove_from_cart():
    """
    Removes a specific item from the cart using $pull.
    $pull removes all array elements matching the given condition.
    """
    product_id = request.form.get("product_id")
    item_type  = request.form.get("type")

    # $pull removes matching array elements without replacing the whole array
    carts_col.update_one(
        {"user_id": ObjectId(current_user.id)},
        {
            "$pull": {
                "items": {
                    "product_id": _oid(product_id),
                    "type":       item_type,
                }
            },
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    flash("Item removed from cart.", "info")
    return redirect(url_for("customer.view_cart"))


# ===========================================================================
# CHECKOUT
# ===========================================================================
@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """
    GET  - shows the checkout review page.
    POST - atomic cart claim (Option A), stock reservation, order/rentals creation,
           with automatic reverse compensation on any failure or exception.
    """
    from pymongo import ReturnDocument

    if current_user.role in ['admin', 'staff']:
        flash("Checkout is disabled for Staff and Admin accounts.", "warning")
        return redirect(url_for("admin.dashboard" if current_user.role == "admin" else "admin.rentals_list"))

    user_oid = ObjectId(current_user.id)

    if request.method == "GET":
        cart = carts_col.find_one({"user_id": user_oid})
        if not cart or not cart.get("items"):
            flash("Your cart is empty.", "warning")
            return redirect(url_for("customer.view_cart"))

        enriched = []
        for item in cart["items"]:
            product = products_col.find_one({"_id": item["product_id"]})
            if product:
                enriched.append({"item": item, "product": product})
        return render_template("customer/checkout.html", enriched=enriched)

    # --- POST: ATOMIC CART CLAIMING (OPTION A) ---
    now = datetime.now(timezone.utc)
    claimed_cart = carts_col.find_one_and_update(
        {"user_id": user_oid, "items.0": {"$exists": True}},
        {"$set": {"items": [], "updated_at": now}},
        return_document=ReturnDocument.BEFORE,
    )

    if not claimed_cart or not claimed_cart.get("items"):
        flash("Your cart is empty. Please add items before checking out.", "warning")
        return redirect(url_for("customer.view_cart"))

    claimed_items = claimed_cart.get("items", [])
    reserved_stock = []
    inserted_order_id = None
    inserted_rental_ids = []

    def rollback_compensation(flash_msg, category="danger"):
        # 1. Delete inserted rental documents if created
        if inserted_rental_ids:
            try:
                rentals_col.delete_many({"_id": {"$in": inserted_rental_ids}})
            except Exception:
                pass
        # 2. Delete inserted order document if created
        if inserted_order_id:
            try:
                orders_col.delete_one({"_id": inserted_order_id})
            except Exception:
                pass
        # 3. Restore any reserved stock
        for pid, q in reserved_stock:
            try:
                products_col.update_one({"_id": pid}, {"$inc": {"stock_qty": q}})
            except Exception:
                pass
        # 4. Restore claimed cart items back into the user's cart
        try:
            carts_col.update_one(
                {"user_id": user_oid},
                {"$set": {"items": claimed_items, "updated_at": datetime.now(timezone.utc)}}
            )
        except Exception:
            pass
        flash(flash_msg, category)
        return redirect(url_for("customer.view_cart"))

    try:
        sell_items = []
        sell_total = 0
        rental_docs = []

        # Step 1: Pre-validate all items
        for item in claimed_items:
            product = products_col.find_one({"_id": item["product_id"]})
            if not product:
                return rollback_compensation("A product in your cart is no longer available.")

            if item["type"] == "sell":
                if product.get("type") == "rent":
                    return rollback_compensation(f"'{product['name']}' is available for rent only.")
                
                qty = item.get("qty", 1)
                if qty < 1:
                    return rollback_compensation(f"Invalid quantity for '{product['name']}'.")

                stock_avail = product.get("stock_qty", 0) or 0
                if stock_avail < qty:
                    return rollback_compensation(f"Insufficient stock for '{product['name']}'. Only {stock_avail} available.")

                unit_price = product.get("sale_price", 0) or 0
                subtotal = unit_price * qty
                sell_total += subtotal
                sell_items.append({
                    "product_id": item["product_id"],
                    "name": product["name"],
                    "qty": qty,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                })

            elif item["type"] == "rent":
                if product.get("type") == "sell":
                    return rollback_compensation(f"'{product['name']}' is available for purchase only.")

                start = item.get("rent_start_date")
                end = item.get("rent_end_date")
                start_str = start.strftime("%Y-%m-%d") if hasattr(start, "strftime") else str(start)[:10]
                end_str = end.strftime("%Y-%m-%d") if hasattr(end, "strftime") else str(end)[:10]

                is_valid, err_msg, start_dt, end_dt = validate_rental_dates(start_str, end_str)
                if not is_valid:
                    return rollback_compensation(f"Rental date error for '{product['name']}': {err_msg}")

                conflict = rentals_col.find_one({
                    "product_id": item["product_id"],
                    "status": {"$in": ["confirmed", "active", "reserved"]},
                    "start_date": {"$lt": end_str},
                    "end_date": {"$gt": start_str},
                })
                if conflict:
                    return rollback_compensation(f"'{product['name']}' is not available for the selected dates ({start_str} to {end_str}). Please choose different dates.")

                days = max((end_dt.date() - start_dt.date()).days, 1)
                ppd = product.get("rent_price_per_day", 0) or 0
                rental_total = ppd * days * item.get("qty", 1)

                rental_docs.append({
                    "user_id": user_oid,
                    "product_id": item["product_id"],
                    "start_date": start_str,
                    "end_date": end_str,
                    "total_price": rental_total,
                    "status": "pending",
                    "created_at": now,
                })

        # Step 2: Atomically reserve stock for all sale items
        for s_item in sell_items:
            res = products_col.update_one(
                {"_id": s_item["product_id"], "stock_qty": {"$gte": s_item["qty"]}},
                {"$inc": {"stock_qty": -s_item["qty"]}}
            )
            if res.modified_count == 1:
                reserved_stock.append((s_item["product_id"], s_item["qty"]))
            else:
                prod = products_col.find_one({"_id": s_item["product_id"]})
                avail = prod.get("stock_qty", 0) if prod else 0
                return rollback_compensation(f"Insufficient stock for '{s_item['name']}'. Only {avail} available.")

        # Step 3: Insert order document if sale items exist
        if sell_items:
            order_doc = {
                "user_id": user_oid,
                "items": sell_items,
                "total": sell_total,
                "status": "pending",
                "stock_deducted": True,
                "created_at": now,
            }
            order_result = orders_col.insert_one(order_doc)
            inserted_order_id = order_result.inserted_id

        # Step 4: Insert rental documents if rental items exist
        if rental_docs:
            rental_result = rentals_col.insert_many(rental_docs)
            inserted_rental_ids = rental_result.inserted_ids

        flash("Payment successful! Your order has been placed.", "success")
        return redirect(url_for("customer.order_confirmation",
                                order_id=str(inserted_order_id) if inserted_order_id else "none"))

    except Exception as ex:
        return rollback_compensation(f"An unexpected error occurred during checkout: {str(ex)}")


# ===========================================================================
# ORDER CONFIRMATION
# ===========================================================================
@customer_bp.route("/order-confirmation")
@login_required
def order_confirmation():
    """Static confirmation page shown after successful checkout."""
    order_id = request.args.get("order_id")
    return render_template("customer/order_confirmation.html", order_id=order_id)


# ===========================================================================
# ORDER HISTORY
# ===========================================================================
@customer_bp.route("/orders")
@login_required
def order_history():
    """
    Shows the current customer's orders and rentals.
    Orders sorted descending by created_at using sort().
    """
    user_oid = ObjectId(current_user.id)

    # Direct PyMongo find with sort — descending order by created_at (-1)
    # The -1 index on orders.created_at (created in seed.py) supports this sort.
    orders = list(
        orders_col.find({"user_id": user_oid}).sort("created_at", -1)
    )

    # Fetch rentals and enrich with live product name (via referenced product_id)
    rentals_raw = list(
        rentals_col.find({"user_id": user_oid}).sort("created_at", -1)
    )
    enriched_rentals = []
    for rental in rentals_raw:
        # REFERENCE: we look up the product by product_id reference to display
        # the product name. The name is not embedded in rentals because
        # product data is managed independently in the products collection.
        product = products_col.find_one(
            {"_id": rental["product_id"]},
            {"name": 1, "brand": 1}  # projection — fetch only needed fields
        )
        enriched_rentals.append({"rental": rental, "product": product})

    return render_template(
        "customer/order_history.html",
        orders=orders,
        enriched_rentals=enriched_rentals,
    )


# ===========================================================================
# CANCEL ORDER (customer)
# ===========================================================================
@customer_bp.route("/orders/<order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    """
    Customer can cancel their own order only while status is 'pending'.
    Conditional update_one - the status check is inside the query filter,
    so MongoDB atomically verifies and updates in one operation.
    If stock was deducted, stock is safely restored.
    """
    order = orders_col.find_one_and_update(
        {
            "_id":     _oid(order_id),
            "user_id": ObjectId(current_user.id),  # ensures customers can only cancel their own orders
            "status":  "pending",                   # only pending orders can be cancelled
        },
        {"$set": {"status": "cancelled"}},
    )
    if order:
        if order.get("stock_deducted"):
            for item in order.get("items", []):
                products_col.update_one(
                    {"_id": item["product_id"]},
                    {"$inc": {"stock_qty": item["qty"]}}
                )
            orders_col.update_one({"_id": order["_id"]}, {"$set": {"stock_deducted": False}})
        flash("Order cancelled successfully.", "success")
    else:
        flash("Order could not be cancelled (it may no longer be pending).", "warning")
    return redirect(url_for("customer.order_history"))


# ===========================================================================
# CANCEL RENTAL (customer)
# ===========================================================================
@customer_bp.route("/rentals/<rental_id>/cancel", methods=["POST"])
@login_required
def cancel_rental(rental_id):
    """
    Customer can cancel their own rental only while status is 'pending'.
    Same conditional update_one pattern as cancel_order.
    Cancelling sets status to 'cancelled', which automatically excludes
    this rental from future availability-conflict checks (those only
    match 'confirmed' or 'active' statuses).
    """
    result = rentals_col.update_one(
        {
            "_id":     _oid(rental_id),
            "user_id": ObjectId(current_user.id),
            "status":  "pending",
        },
        {"$set": {"status": "cancelled"}},
    )
    if result.modified_count == 1:
        flash("Rental cancelled successfully.", "success")
    else:
        flash("Rental could not be cancelled.", "warning")
    return redirect(url_for("customer.order_history"))