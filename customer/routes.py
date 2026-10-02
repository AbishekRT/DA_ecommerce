"""
customer/routes.py
All customer-facing routes: catalog, product detail, compare,
cart management, checkout, and order history.

Every MongoDB operation is a direct, explicit PyMongo call.
No ODM, no repository layer — every query is readable in-place.
"""

from datetime import datetime, timezone, date
from bson import ObjectId
from bson.errors import InvalidId

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


# ===========================================================================
# HELPER — safe ObjectId conversion
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

    return render_template(
        "customer/product_detail.html",
        product=product,
        category=category,
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
        try:
            start_str = request.form.get("rent_start_date") or request.form.get("rental_start") or ""
            end_str   = request.form.get("rent_end_date") or request.form.get("rental_end") or ""
            new_item["rent_start_date"] = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            new_item["rent_end_date"]   = datetime.strptime(end_str,   "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            flash("Invalid rental dates specified.", "danger")
            return redirect(url_for("customer.product_detail", product_id=product_id))

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
    GET  — shows the checkout review page.
    POST — dummy payment: creates order/rental documents and clears the cart.
    """
    if current_user.role in ['admin', 'staff']:
        flash("Checkout is disabled for Staff and Admin accounts.", "warning")
        return redirect(url_for("admin.dashboard" if current_user.role == "admin" else "admin.rentals_list"))

    user_oid = ObjectId(current_user.id)
    cart = carts_col.find_one({"user_id": user_oid})

    if not cart or not cart.get("items"):
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.view_cart"))

    # Enrich cart items for the review page
    enriched = []
    for item in cart["items"]:
        product = products_col.find_one({"_id": item["product_id"]})
        if product:
            enriched.append({"item": item, "product": product})

    if request.method == "POST":
        now = datetime.now(timezone.utc)
        sell_items   = []
        sell_total   = 0
        rental_docs  = []

        for entry in enriched:
            item    = entry["item"]
            product = entry["product"]

            if item["type"] == "sell":
                unit_price = product.get("sale_price", 0) or 0
                subtotal   = unit_price * item["qty"]
                sell_total += subtotal
                # EMBED: order items embed a price snapshot at checkout time.
                # We freeze name, price, and qty so the order history is
                # accurate even if product prices change later.
                # This differs from the cart, which references live product data.
                sell_items.append({
                    "product_id": item["product_id"],  # kept for reference only
                    "name":       product["name"],
                    "qty":        item["qty"],
                    "unit_price": unit_price,
                    "subtotal":   subtotal,
                })

            elif item["type"] == "rent":
                start = item.get("rent_start_date")
                end   = item.get("rent_end_date")
                days  = max((end - start).days, 1) if start and end else 1
                ppd   = product.get("rent_price_per_day", 0) or 0
                total = ppd * days * item["qty"]

                # ---- Rental availability conflict check ----
                # Core NoSQL query: find any CONFIRMED, ACTIVE, or RESERVED rental for
                # the same product whose date range overlaps the requested range.
                # Two ranges [A,B] and [C,D] overlap when A < D AND C < B.
                # Cancelled rentals are excluded by the status $in filter —
                # cancelling a rental automatically frees up those dates
                # with no extra "release" step needed.
                start_str = start.strftime("%Y-%m-%d") if hasattr(start, "strftime") else str(start)
                end_str   = end.strftime("%Y-%m-%d") if hasattr(end, "strftime") else str(end)

                conflict = rentals_col.find_one({
                    "product_id": item["product_id"],
                    "status": {"$in": ["confirmed", "active", "reserved"]},
                    "start_date": {"$lt": end_str},
                    "end_date":   {"$gt": start_str},
                })
                if conflict:
                    flash(
                        f"'{product['name']}' is not available for the selected dates. "
                        "Please choose different dates.",
                        "danger",
                    )
                    return redirect(url_for("customer.view_cart"))

                # REFERENCE: rentals.product_id is a reference (not embedded)
                # because the availability-conflict query must filter rentals
                # by product — this requires querying rentals independently
                # of product documents. Embedding product data here would
                # make that cross-document query impossible.
                rental_doc = {
                    "user_id":     user_oid,
                    "product_id":  item["product_id"],
                    "start_date":  start_str,
                    "end_date":    end_str,
                    "total_price": total,
                    "status":      "pending",
                    "created_at":  now,
                }
                rental_docs.append(rental_doc)

        # --- Create order document if there are sale items ---
        order_id = None
        if sell_items:
            order_doc = {
                # REFERENCE: user_id is a reference to the users collection.
                # Embedding full user data here would duplicate it across every
                # order and would go stale if the user updates their profile.
                "user_id":    user_oid,
                # EMBED: items array is embedded because it is a frozen snapshot
                # of what was purchased — prices and names are captured at checkout
                # time and are never updated independently.
                "items":      sell_items,
                "total":      sell_total,
                "status":     "pending",
                "created_at": now,
            }
            result = orders_col.insert_one(order_doc)
            order_id = result.inserted_id

        # --- Create rental documents ---
        rental_ids = []
        if rental_docs:
            result = rentals_col.insert_many(rental_docs)
            rental_ids = result.inserted_ids

        # --- Clear the cart after successful checkout ---
        # $set replaces the items array with an empty list
        carts_col.update_one(
            {"user_id": user_oid},
            {"$set": {"items": [], "updated_at": now}},
        )

        flash("Payment successful! Your order has been placed.", "success")
        return redirect(url_for("customer.order_confirmation",
                                order_id=str(order_id) if order_id else "none"))

    return render_template("customer/checkout.html", enriched=enriched)


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