"""Customer routes for catalog, product detail, comparison, cart, checkout, and order history."""

from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort, session, current_app
)
from flask_login import login_required, current_user

from extensions import (
    products_col, categories_col, carts_col,
    orders_col, rentals_col
)

customer_bp = Blueprint("customer", __name__, template_folder="../templates/customer")

# Sri Lanka timezone (UTC+5:30)
SL_TZ = timezone(timedelta(hours=5, minutes=30))


def get_sl_now():
    """Return current datetime in Sri Lanka timezone."""
    return datetime.now(SL_TZ)


def get_sl_today():
    """Return current date in Sri Lanka timezone."""
    return datetime.now(SL_TZ).date()


def validate_rental_dates(start_str, end_str):
    """Validate rental date range constraints."""
    if not start_str or not end_str:
        return False, "Both start and end dates are required for rental bookings.", None, None
    try:
        start_d = datetime.strptime(str(start_str).strip(), "%Y-%m-%d").date()
        end_d = datetime.strptime(str(end_str).strip(), "%Y-%m-%d").date()
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
    end_utc = datetime(end_d.year, end_d.month, end_d.day, tzinfo=timezone.utc)
    return True, "", start_utc, end_utc


# Helper: safe ObjectId conversion
def _oid(s):
    try:
        return ObjectId(s)
    except (InvalidId, TypeError):
        abort(404)


# Catalog
@customer_bp.route("/")
@customer_bp.route("/catalog")
def catalog():
    """List products with optional search, category, type, and sort filters."""
    query = {"is_active": {"$ne": False}}

    cat_id = request.args.get("category")
    if cat_id:
        try:
            query["category_id"] = ObjectId(cat_id)
        except Exception:
            pass

    type_filter = request.args.get("type")
    if type_filter in ("sell", "rent"):
        query["type"] = {"$in": [type_filter, "both"]}

    q = request.args.get("q", "").strip()
    if q:
        import re
        q_safe = re.escape(q)
        query["$or"] = [
            {"name": {"$regex": q_safe, "$options": "i"}},
            {"brand": {"$regex": q_safe, "$options": "i"}},
            {"description": {"$regex": q_safe, "$options": "i"}},
            {"specs.resolution": {"$regex": q_safe, "$options": "i"}},
        ]

    products = list(products_col.find(query))

    sort_by = request.args.get("sort", "featured")
    if sort_by == "price_low":
        products = sorted(products, key=lambda p: (p.get("sale_price") or p.get("rent_price_per_day") or 0))
    elif sort_by == "price_high":
        products = sorted(products, key=lambda p: (p.get("sale_price") or p.get("rent_price_per_day") or 0), reverse=True)
    elif sort_by == "name_asc":
        products = sorted(products, key=lambda p: p.get("name", "").lower())

    for p in products:
        if "name" in p and isinstance(p["name"], str):
            p["name"] = p["name"].replace('—', ' - ').replace('–', ' - ').replace('&mdash;', ' - ')

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


# Product Detail
@customer_bp.route("/product/<product_id>")
def product_detail(product_id):
    """View details and pricing for a single product."""
    product = products_col.find_one({"_id": _oid(product_id), "is_active": {"$ne": False}})
    if not product:
        abort(404)

    category = categories_col.find_one({"_id": product["category_id"]})
    sl_today = get_sl_today().strftime("%Y-%m-%d")

    if product and "name" in product and isinstance(product["name"], str):
        product["name"] = product["name"].replace('—', ' - ').replace('–', ' - ').replace('&mdash;', ' - ')

    return render_template(
        "customer/product_detail.html",
        product=product,
        category=category,
        sl_today=sl_today,
    )


# Product Comparison
@customer_bp.route("/compare")
def compare():
    """Side-by-side comparison of selected products."""
    ids = request.args.getlist("ids")
    products = []

    if ids:
        try:
            oid_list = [ObjectId(i) for i in ids if i]
        except Exception:
            oid_list = []

        if oid_list:
            fetched = list(products_col.find({"_id": {"$in": oid_list}, "is_active": {"$ne": False}}))
            p_map = {str(p["_id"]): p for p in fetched}
            products = [p_map[i] for i in ids if i in p_map]

    for p in products:
        if "name" in p and isinstance(p["name"], str):
            p["name"] = p["name"].replace('—', ' - ').replace('–', ' - ').replace('&mdash;', ' - ')

    all_products = list(products_col.find({"is_active": {"$ne": False}}, {"name": 1, "brand": 1}).sort("name", 1))
    for p in all_products:
        if "name" in p and isinstance(p["name"], str):
            p["name"] = p["name"].replace('—', ' - ').replace('–', ' - ').replace('&mdash;', ' - ')

    return render_template(
        "customer/compare.html",
        products=products,
        all_products=all_products,
        selected_ids=ids,
    )


# Cart
@customer_bp.route("/cart")
@login_required
def view_cart():
    """View customer shopping cart."""
    if current_user.role in ['admin', 'staff']:
        flash("Shopping cart is reserved for Customer accounts. Staff and Admins manage operations via the Management Console.", "info")
        return redirect(url_for("admin.dashboard" if current_user.role == "admin" else "admin.rentals_list"))

    cart = carts_col.find_one({"user_id": ObjectId(current_user.id)})
    enriched_items = []
    cart_total = 0

    if cart:
        for item in cart.get("items", []):
            product = products_col.find_one({"_id": item["product_id"]})
            if product:
                if item["type"] == "sell":
                    unit_price = product.get("sale_price", 0) or 0
                    subtotal = unit_price * item["qty"]
                else:
                    start = item.get("rent_start_date")
                    end = item.get("rent_end_date")
                    days = (end - start).days if start and end else 0
                    days = max(days, 1)
                    unit_price = product.get("rent_price_per_day", 0) or 0
                    subtotal = unit_price * days * item["qty"]
                cart_total += subtotal
                enriched_items.append({
                    "product": product,
                    "item": item,
                    "subtotal": subtotal,
                    "days": (end - start).days if item["type"] == "rent" and start and end else None,
                })

    return render_template(
        "customer/cart.html",
        enriched_items=enriched_items,
        cart_total=cart_total,
    )


@customer_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    """Add item to cart or update existing cart document."""
    if current_user.is_authenticated and current_user.role in ['admin', 'staff']:
        flash("Shopping cart is disabled for Administrative and Staff accounts.", "warning")
        return redirect(url_for("customer.catalog"))

    product_id = request.form.get("product_id")
    item_type = request.form.get("type")

    product = products_col.find_one({"_id": _oid(product_id), "is_active": {"$ne": False}})
    if not product:
        abort(404)

    # Validate mode vs product availability
    if item_type == "sell" and product.get("type") == "rent":
        flash("This product is available for rent only.", "warning")
        return redirect(url_for("customer.product_detail", product_id=product_id))
    if item_type == "rent" and product.get("type") == "sell":
        flash("This product is available for purchase only.", "warning")
        return redirect(url_for("customer.product_detail", product_id=product_id))

    # Quantity validation
    if item_type == "rent":
        qty = 1
    else:
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

    start_str = request.form.get("rent_start_date") or request.form.get("rental_start") or ""
    end_str = request.form.get("rent_end_date") or request.form.get("rental_end") or ""

    if not current_user.is_authenticated:
        session["pending_cart_item"] = {
            "product_id": product_id,
            "type": item_type,
            "qty": qty,
            "rent_start_date": start_str if item_type == "rent" else "",
            "rent_end_date": end_str if item_type == "rent" else "",
        }
        flash(f"Please sign in or create an account to add '{product['name']}' to your cart.", "info")
        return redirect(url_for("auth.login", next=url_for("customer.view_cart")))

    new_item = {
        "product_id": _oid(product_id),
        "type": item_type,
        "qty": qty,
    }

    if item_type == "rent":
        is_valid, err_msg, start_dt, end_dt = validate_rental_dates(start_str, end_str)
        if not is_valid:
            flash(err_msg, "danger")
            return redirect(url_for("customer.product_detail", product_id=product_id))
        new_item["rent_start_date"] = start_dt
        new_item["rent_end_date"] = end_dt

    user_oid = ObjectId(current_user.id)

    # Check for duplicate item in cart
    existing_cart = carts_col.find_one({"user_id": user_oid})
    if existing_cart:
        duplicate = any(
            str(i["product_id"]) == product_id and i["type"] == item_type
            for i in existing_cart.get("items", [])
        )
        if duplicate:
            flash("This item is already in your cart.", "warning")
            return redirect(url_for("customer.view_cart"))

    carts_col.update_one(
        {"user_id": user_oid},
        {
            "$push": {"items": new_item},
            "$set": {"updated_at": datetime.now(timezone.utc)},
            "$setOnInsert": {"user_id": user_oid},
        },
        upsert=True,
    )
    flash("Item added to cart.", "success")
    if request.form.get("action") == "buy_now":
        return redirect(url_for("customer.checkout"))
    return redirect(url_for("customer.view_cart"))


@customer_bp.route("/cart/remove", methods=["POST"])
@login_required
def remove_from_cart():
    """Remove item from cart array."""
    product_id = request.form.get("product_id")
    item_type = request.form.get("type")

    carts_col.update_one(
        {"user_id": ObjectId(current_user.id)},
        {
            "$pull": {
                "items": {
                    "product_id": _oid(product_id),
                    "type": item_type,
                }
            },
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    flash("Item removed from cart.", "info")
    return redirect(url_for("customer.view_cart"))


# Checkout
@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """Order review and placement with stock deduction and rollback protection."""
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
                qty = item.get("qty", 1)
                if item["type"] == "sell":
                    unit_price = product.get("sale_price") or 0
                    line_subtotal = unit_price * qty
                    days = None
                else:
                    start = item.get("rent_start_date")
                    end = item.get("rent_end_date")
                    days = max((end - start).days, 1) if start and end else 1
                    ppd = product.get("rent_price_per_day") or 0
                    line_subtotal = ppd * days * qty
                enriched.append({
                    "item": item,
                    "product": product,
                    "line_subtotal": line_subtotal,
                    "days": days,
                })

        purchases_subtotal = sum(r["line_subtotal"] for r in enriched if r["item"]["type"] == "sell")
        rentals_subtotal = sum(r["line_subtotal"] for r in enriched if r["item"]["type"] == "rent")
        grand_total = purchases_subtotal + rentals_subtotal

        return render_template(
            "customer/checkout.html",
            enriched=enriched,
            purchases_subtotal=purchases_subtotal,
            rentals_subtotal=rentals_subtotal,
            grand_total=grand_total,
        )

    # Atomic cart claim to prevent duplicate submissions
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
        # Roll back inserted rentals
        if inserted_rental_ids:
            try:
                rentals_col.delete_many({"_id": {"$in": inserted_rental_ids}})
            except Exception:
                pass
        # Roll back inserted order
        if inserted_order_id:
            try:
                orders_col.delete_one({"_id": inserted_order_id})
            except Exception:
                pass
        # Restore reserved stock
        for pid, q in reserved_stock:
            try:
                products_col.update_one({"_id": pid}, {"$inc": {"stock_qty": q}})
            except Exception:
                pass
        # Restore claimed items back into cart
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

        # Validate items and availability
        for item in claimed_items:
            product = products_col.find_one({"_id": item["product_id"], "is_active": {"$ne": False}})
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
                    "status": {"$in": ["pending", "confirmed", "active", "reserved"]},
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

        # Atomically deduct stock for purchases
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

        # Create purchase order document
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

        # Create rental booking documents
        if rental_docs:
            rental_result = rentals_col.insert_many(rental_docs)
            inserted_rental_ids = rental_result.inserted_ids

        flash("Order confirmed. Payment is simulated for this demonstration.", "success")
        return redirect(url_for("customer.order_confirmation",
                                order_id=str(inserted_order_id) if inserted_order_id else "none"))

    except Exception as ex:
        current_app.logger.exception("Checkout exception: %s", ex)
        return rollback_compensation("An unexpected error occurred while processing checkout. Please try again.")


# Order Confirmation
@customer_bp.route("/order-confirmation")
@login_required
def order_confirmation():
    """Order placement confirmation view."""
    order_id = request.args.get("order_id")
    if order_id and order_id != "none":
        try:
            target_oid = ObjectId(order_id)
        except (InvalidId, TypeError):
            return redirect(url_for("customer.order_history"))
        order = orders_col.find_one({
            "_id": target_oid,
            "user_id": ObjectId(current_user.id),
        })
        if not order:
            return redirect(url_for("customer.order_history"))
    return render_template("customer/order_confirmation.html", order_id=order_id)


# Order History
@customer_bp.route("/orders")
@login_required
def order_history():
    """Customer order history and active rentals."""
    user_oid = ObjectId(current_user.id)

    orders = list(
        orders_col.find({"user_id": user_oid}).sort("created_at", -1)
    )

    rentals_raw = list(
        rentals_col.find({"user_id": user_oid}).sort("created_at", -1)
    )
    enriched_rentals = []
    for rental in rentals_raw:
        product = products_col.find_one(
            {"_id": rental["product_id"]},
            {"name": 1, "brand": 1}
        )
        enriched_rentals.append({"rental": rental, "product": product})

    return render_template(
        "customer/order_history.html",
        orders=orders,
        enriched_rentals=enriched_rentals,
    )


# Cancel Order
@customer_bp.route("/orders/<order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    """Cancel pending order and restore stock."""
    order = orders_col.find_one_and_update(
        {
            "_id": _oid(order_id),
            "user_id": ObjectId(current_user.id),
            "status": "pending",
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


# Cancel Rental
@customer_bp.route("/rentals/<rental_id>/cancel", methods=["POST"])
@login_required
def cancel_rental(rental_id):
    """Cancel pending rental reservation."""
    result = rentals_col.update_one(
        {
            "_id": _oid(rental_id),
            "user_id": ObjectId(current_user.id),
            "status": "pending",
        },
        {"$set": {"status": "cancelled"}},
    )
    if result.modified_count == 1:
        flash("Rental cancelled successfully.", "success")
    else:
        flash("Rental could not be cancelled.", "warning")
    return redirect(url_for("customer.order_history"))