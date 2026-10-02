"""
admin/routes.py
Administration and Staff Operations routes: product CRUD, order management, rental management,
and aggregation pipeline demonstrations.

Role Access:
  - Super Admin ('admin'): Full access (Financial Dashboard, Revenue Aggregation, Product Deletion).
  - Operations Staff ('staff'): Operational access (Orders, Rentals, Product Creation/Editing).
  - Customer ('customer'): Restricted (403 Forbidden on all admin routes).
"""

from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, abort
)
from flask_login import login_required, current_user

from extensions import (
    products_col, categories_col,
    orders_col, rentals_col, users_col
)
from auth.decorators import role_required

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


REVENUE_STATUSES = ["confirmed", "processing", "shipped", "completed"]

def _oid(s):
    try:
        return ObjectId(s)
    except (InvalidId, TypeError):
        abort(404)


# ===========================================================================
# DASHBOARD (Admin Only)
# ===========================================================================
@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    """
    Financial & System Summary Dashboard.
    Restricted to 'admin' role. Staff are directed to operational views.
    """
    total_products  = products_col.count_documents({})
    total_orders    = orders_col.count_documents({})
    total_rentals   = rentals_col.count_documents({})
    total_customers = users_col.count_documents({"role": "customer"})

    # -----------------------------------------------------------------------
    # AGGREGATION PIPELINE 1: Revenue by category
    # Calculates total revenue from orders grouped by product category.
    # -----------------------------------------------------------------------
    revenue_pipeline = [
        {"$match": {"status": {"$in": REVENUE_STATUSES}}},
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.product_id",
                "foreignField": "_id",
                "as": "product",
            }
        },
        {"$unwind": "$product"},
        {
            "$lookup": {
                "from": "categories",
                "localField": "product.category_id",
                "foreignField": "_id",
                "as": "category",
            }
        },
        {"$unwind": "$category"},
        {
            "$group": {
                "_id": "$category.name",
                "revenue": {
                    "$sum": {
                        "$multiply": ["$items.unit_price", "$items.qty"]
                    }
                },
            }
        },
        {"$sort": {"revenue": -1}},
    ]
    revenue_by_category = list(orders_col.aggregate(revenue_pipeline))

    # -----------------------------------------------------------------------
    # AGGREGATION PIPELINE 2: Rental equipment utilisation
    # Calculates total duration in days each projector was rented.
    # -----------------------------------------------------------------------
    utilisation_pipeline = [
        {"$match": {"status": {"$in": ["active", "returned"]}}},
        {
            "$project": {
                "product_id": 1,
                "days": {
                    "$divide": [
                        {"$subtract": [
                            {"$dateFromString": {"dateString": "$end_date"}},
                            {"$dateFromString": {"dateString": "$start_date"}},
                        ]},
                        86400000,
                    ]
                },
            }
        },
        {
            "$group": {
                "_id": "$product_id",
                "total_days": {"$sum": "$days"},
                "booking_count": {"$sum": 1},
            }
        },
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "_id",
                "as": "product",
            }
        },
        {"$unwind": "$product"},
        {
            "$project": {
                "name": "$product.name",
                "brand": "$product.brand",
                "total_days": 1,
                "booking_count": 1,
            }
        },
        {"$sort": {"total_days": -1}},
    ]
    rental_utilisation = list(rentals_col.aggregate(utilisation_pipeline))

    return render_template(
        "admin/dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        total_rentals=total_rentals,
        total_customers=total_customers,
        revenue_by_category=revenue_by_category,
        rental_utilisation=rental_utilisation,
    )


# ===========================================================================
# PRODUCT MANAGEMENT — LIST (Admin & Staff)
# ===========================================================================
@admin_bp.route("/products")
@login_required
@role_required("admin", "staff")
def products_list():
    """Lists all products with resolved category names."""
    products = list(products_col.find().sort("created_at", -1))
    categories = {str(c["_id"]): c["name"] for c in categories_col.find()}
    return render_template(
        "admin/products.html",
        products=products,
        categories=categories,
    )


# ===========================================================================
# PRODUCT MANAGEMENT — CREATE (Admin & Staff)
# ===========================================================================
@admin_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@role_required("admin", "staff")
def product_create():
    """Create a new product document."""
    categories = list(categories_col.find())

    if request.method == "POST":
        f = request.form
        connectivity = [c.strip() for c in f.get("connectivity", "").split(",") if c.strip()]

        product_doc = {
            "name":       f.get("name", "").strip(),
            "brand":      f.get("brand", "").strip(),
            "category_id": ObjectId(f.get("category_id")),
            "type":        f.get("type"),
            "sale_price":  float(f.get("sale_price") or 0) or None,
            "rent_price_per_day": float(f.get("rent_price_per_day") or 0) or None,
            "stock_qty":   int(f.get("stock_qty", 0)),
            "image_url":   f.get("image_url", "").strip(),
            "description": f.get("description", "").strip(),
            "specs": {
                "resolution":       f.get("resolution", "").strip(),
                "brightness_lumens": int(f.get("brightness_lumens") or 0),
                "throw_distance":   f.get("throw_distance", "").strip(),
                "connectivity":     connectivity,
            },
            "created_at": datetime.now(timezone.utc),
        }

        products_col.insert_one(product_doc)
        flash("Product created successfully.", "success")
        return redirect(url_for("admin.products_list"))

    return render_template("admin/product_form.html", product=None, categories=categories, action="Create")


# ===========================================================================
# PRODUCT MANAGEMENT — EDIT (Admin & Staff)
# ===========================================================================
@admin_bp.route("/products/<product_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "staff")
def product_edit(product_id):
    """Edit an existing product document."""
    product    = products_col.find_one({"_id": _oid(product_id)})
    categories = list(categories_col.find())
    if not product:
        abort(404)

    if request.method == "POST":
        f = request.form
        connectivity = [c.strip() for c in f.get("connectivity", "").split(",") if c.strip()]

        products_col.update_one(
            {"_id": _oid(product_id)},
            {"$set": {
                "name":       f.get("name", "").strip(),
                "brand":      f.get("brand", "").strip(),
                "category_id": ObjectId(f.get("category_id")),
                "type":        f.get("type"),
                "sale_price":  float(f.get("sale_price") or 0) or None,
                "rent_price_per_day": float(f.get("rent_price_per_day") or 0) or None,
                "stock_qty":   int(f.get("stock_qty", 0)),
                "image_url":   f.get("image_url", "").strip(),
                "description": f.get("description", "").strip(),
                "specs": {
                    "resolution":        f.get("resolution", "").strip(),
                    "brightness_lumens": int(f.get("brightness_lumens") or 0),
                    "throw_distance":    f.get("throw_distance", "").strip(),
                    "connectivity":      connectivity,
                },
            }},
        )
        flash("Product updated successfully.", "success")
        return redirect(url_for("admin.products_list"))

    return render_template("admin/product_form.html", product=product, categories=categories, action="Edit")


# ===========================================================================
# PRODUCT MANAGEMENT — DELETE (Admin ONLY)
# ===========================================================================
@admin_bp.route("/products/<product_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def product_delete(product_id):
    """Hard delete a product document. Restricted to Admin."""
    products_col.delete_one({"_id": _oid(product_id)})
    flash("Product deleted from catalog.", "warning")
    return redirect(url_for("admin.products_list"))


# ===========================================================================
# ORDERS MANAGEMENT (Admin & Staff)
# ===========================================================================
@admin_bp.route("/orders")
@login_required
@role_required("admin", "staff")
def orders_list():
    """All customer orders, newest first."""
    orders = list(orders_col.find().sort("created_at", -1))
    for order in orders:
        user = users_col.find_one({"_id": order["user_id"]}, {"name": 1, "email": 1})
        order["customer"] = user
    return render_template("admin/orders.html", orders=orders)


@admin_bp.route("/orders/<order_id>/status", methods=["POST"])
@login_required
@role_required("admin", "staff")
def update_order_status(order_id):
    """Update order status (pending -> confirmed -> processing -> shipped -> completed -> cancelled)."""
    new_status = request.form.get("status")
    valid = {"pending", "confirmed", "processing", "shipped", "completed", "cancelled"}
    if new_status not in valid:
        flash("Invalid status specified.", "danger")
        return redirect(url_for("admin.orders_list"))

    order = orders_col.find_one({"_id": _oid(order_id)})
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders_list"))

    if new_status == "cancelled" and order.get("status") != "cancelled":
        if order.get("stock_deducted"):
            for item in order.get("items", []):
                products_col.update_one(
                    {"_id": item["product_id"]},
                    {"$inc": {"stock_qty": item["qty"]}}
                )
            orders_col.update_one({"_id": order["_id"]}, {"$set": {"stock_deducted": False}})

    orders_col.update_one(
        {"_id": _oid(order_id)},
        {"$set": {"status": new_status}},
    )
    flash(f"Order status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.orders_list"))


# ===========================================================================
# RENTALS MANAGEMENT (Admin & Staff)
# ===========================================================================
@admin_bp.route("/rentals")
@login_required
@role_required("admin", "staff")
def rentals_list():
    """All rental bookings with resolved product and customer details."""
    rentals = list(rentals_col.find().sort("created_at", -1))
    for rental in rentals:
        rental["product"] = products_col.find_one({"_id": rental["product_id"]}, {"name": 1})
        rental["customer"] = users_col.find_one({"_id": rental["user_id"]}, {"name": 1, "email": 1})
    return render_template("admin/rentals.html", rentals=rentals)


@admin_bp.route("/rentals/<rental_id>/status", methods=["POST"])
@login_required
@role_required("admin", "staff")
def update_rental_status(rental_id):
    """Update rental status (pending -> confirmed -> reserved -> active -> returned -> cancelled)."""
    new_status = request.form.get("status")
    valid = {"pending", "confirmed", "reserved", "active", "returned", "cancelled"}
    if new_status not in valid:
        flash("Invalid rental status specified.", "danger")
        return redirect(url_for("admin.rentals_list"))

    rentals_col.update_one(
        {"_id": _oid(rental_id)},
        {"$set": {"status": new_status}},
    )
    flash(f"Rental status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.rentals_list"))


# ===========================================================================
# USER DIRECTORY (Admin & Staff)
# ===========================================================================
@admin_bp.route("/users")
@login_required
@role_required("admin", "staff")
def users_list():
    """All registered user accounts and RBAC roles."""
    users = list(users_col.find().sort("created_at", -1))
    for u in users:
        u["order_count"] = orders_col.count_documents({"user_id": u["_id"]})
        u["rental_count"] = rentals_col.count_documents({"user_id": u["_id"]})
    return render_template("admin/users.html", users=users)