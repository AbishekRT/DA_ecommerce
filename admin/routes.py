"""Admin and staff management routes."""

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


# Admin Dashboard
@admin_bp.route("/")
@login_required
@role_required("admin")
def dashboard():
    """Summary dashboard and metrics for administrator."""
    total_products = products_col.count_documents({"is_active": {"$ne": False}})
    total_orders = orders_col.count_documents({})
    total_rentals = rentals_col.count_documents({})
    total_customers = users_col.count_documents({"role": "customer"})

    # Revenue aggregated by category
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
        {"$unwind": {"path": "$product", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "categories",
                "localField": "product.category_id",
                "foreignField": "_id",
                "as": "category",
            }
        },
        {"$unwind": {"path": "$category", "preserveNullAndEmptyArrays": True}},
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

    # Rental utilization in days
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


# Product Management: List
@admin_bp.route("/products")
@login_required
@role_required("admin", "staff")
def products_list():
    """List inventory products."""
    products = list(products_col.find({"is_active": {"$ne": False}}).sort("created_at", -1))
    categories = {str(c["_id"]): c["name"] for c in categories_col.find()}
    return render_template(
        "admin/products.html",
        products=products,
        categories=categories,
    )


# Product Management: Create
@admin_bp.route("/products/new", methods=["GET", "POST"])
@login_required
@role_required("admin", "staff")
def product_create():
    """Add a new product to inventory."""
    categories = list(categories_col.find())

    if request.method == "POST":
        f = request.form
        
        p_type = f.get("type")
        s_price = float(f.get("sale_price") or 0)
        r_price = float(f.get("rent_price_per_day") or 0)
        try:
            stock_qty = int(f.get("stock_qty", 0) or 0)
        except (ValueError, TypeError):
            stock_qty = -1
        if stock_qty < 0:
            flash("Stock cannot be negative.", "danger")
            return redirect(url_for("admin.product_create"))
        if p_type in ["sell", "both"] and s_price <= 0:
            flash("Sale price must be strictly positive.", "danger")
            return redirect(url_for("admin.product_create"))
        if p_type in ["rent", "both"] and r_price <= 0:
            flash("Rent price must be strictly positive.", "danger")
            return redirect(url_for("admin.product_create"))

        connectivity = [c.strip() for c in f.get("connectivity", "").split(",") if c.strip()]

        product_doc = {
            "name": f.get("name", "").strip(),
            "brand": f.get("brand", "").strip(),
            "category_id": ObjectId(f.get("category_id")),
            "type": f.get("type"),
            "sale_price": float(f.get("sale_price") or 0) or None,
            "rent_price_per_day": float(f.get("rent_price_per_day") or 0) or None,
            "stock_qty": stock_qty,
            "image_url": f.get("image_url", "").strip(),
            "description": f.get("description", "").strip(),
            "specs": {
                "resolution": f.get("resolution", "").strip(),
                "brightness_lumens": int(f.get("brightness_lumens") or 0),
                "throw_distance": f.get("throw_distance", "").strip(),
                "connectivity": connectivity,
            },
            "created_at": datetime.now(timezone.utc),
        }

        products_col.insert_one(product_doc)
        flash("Product created successfully.", "success")
        return redirect(url_for("admin.products_list"))

    return render_template("admin/product_form.html", product=None, categories=categories, action="Create")


# Product Management: Edit
@admin_bp.route("/products/<product_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "staff")
def product_edit(product_id):
    """Update existing product details."""
    product = products_col.find_one({"_id": _oid(product_id)})
    categories = list(categories_col.find())
    if not product:
        abort(404)

    if request.method == "POST":
        f = request.form
        
        p_type = f.get("type")
        s_price = float(f.get("sale_price") or 0)
        r_price = float(f.get("rent_price_per_day") or 0)
        try:
            stock_qty = int(f.get("stock_qty", 0) or 0)
        except (ValueError, TypeError):
            stock_qty = -1
        if stock_qty < 0:
            flash("Stock cannot be negative.", "danger")
            return redirect(url_for("admin.product_edit", product_id=product_id))
        if p_type in ["sell", "both"] and s_price <= 0:
            flash("Sale price must be strictly positive.", "danger")
            return redirect(url_for("admin.product_edit", product_id=product_id))
        if p_type in ["rent", "both"] and r_price <= 0:
            flash("Rent price must be strictly positive.", "danger")
            return redirect(url_for("admin.product_edit", product_id=product_id))

        connectivity = [c.strip() for c in f.get("connectivity", "").split(",") if c.strip()]

        products_col.update_one(
            {"_id": _oid(product_id)},
            {"$set": {
                "name": f.get("name", "").strip(),
                "brand": f.get("brand", "").strip(),
                "category_id": ObjectId(f.get("category_id")),
                "type": f.get("type"),
                "sale_price": float(f.get("sale_price") or 0) or None,
                "rent_price_per_day": float(f.get("rent_price_per_day") or 0) or None,
                "stock_qty": stock_qty,
                "image_url": f.get("image_url", "").strip(),
                "description": f.get("description", "").strip(),
                "specs.resolution": f.get("resolution", "").strip(),
                "specs.brightness_lumens": int(f.get("brightness_lumens") or 0),
                "specs.throw_distance": f.get("throw_distance", "").strip(),
                "specs.connectivity": connectivity,
            }},
        )
        flash("Product updated successfully.", "success")
        return redirect(url_for("admin.products_list"))

    return render_template("admin/product_form.html", product=product, categories=categories, action="Edit")


# Product Management: Delete
@admin_bp.route("/products/<product_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def product_delete(product_id):
    """Soft delete product by marking inactive."""
    products_col.update_one({"_id": _oid(product_id)}, {"$set": {"is_active": False}})
    flash("Product deleted from catalog.", "warning")
    return redirect(url_for("admin.products_list"))


# Orders Management
@admin_bp.route("/orders")
@login_required
@role_required("admin", "staff")
def orders_list():
    """List customer orders."""
    orders = list(orders_col.find().sort("created_at", -1))
    for order in orders:
        user = users_col.find_one({"_id": order["user_id"]}, {"name": 1, "email": 1})
        order["customer"] = user
    return render_template("admin/orders.html", orders=orders)


@admin_bp.route("/orders/<order_id>/status", methods=["POST"])
@login_required
@role_required("admin", "staff")
def update_order_status(order_id):
    """Update order fulfillment status."""
    new_status = request.form.get("status")
    valid = {"pending", "confirmed", "processing", "shipped", "completed", "cancelled"}
    if new_status not in valid:
        flash("Invalid status specified.", "danger")
        return redirect(url_for("admin.orders_list"))

    order = orders_col.find_one({"_id": _oid(order_id)})
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders_list"))

    if order.get("status") == "cancelled" and new_status != "cancelled":
        flash("Cannot modify an order that has already been cancelled.", "danger")
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


# Rentals Management
@admin_bp.route("/rentals")
@login_required
@role_required("admin", "staff")
def rentals_list():
    """List rental reservations."""
    rentals = list(rentals_col.find().sort("created_at", -1))
    for rental in rentals:
        rental["product"] = products_col.find_one({"_id": rental["product_id"]}, {"name": 1})
        rental["customer"] = users_col.find_one({"_id": rental["user_id"]}, {"name": 1, "email": 1})
    return render_template("admin/rentals.html", rentals=rentals)


@admin_bp.route("/rentals/<rental_id>/status", methods=["POST"])
@login_required
@role_required("admin", "staff")
def update_rental_status(rental_id):
    """Update rental reservation status."""
    new_status = request.form.get("status")
    valid = {"pending", "confirmed", "reserved", "active", "returned", "cancelled"}
    if new_status not in valid:
        flash("Invalid rental status specified.", "danger")
        return redirect(url_for("admin.rentals_list"))

    rental = rentals_col.find_one({"_id": _oid(rental_id)})
    if not rental:
        flash("Rental not found.", "danger")
        return redirect(url_for("admin.rentals_list"))

    if new_status in ["pending", "confirmed", "active", "reserved"]:
        conflict = rentals_col.find_one({
            "_id": {"$ne": rental["_id"]},
            "product_id": rental["product_id"],
            "status": {"$in": ["pending", "confirmed", "active", "reserved"]},
            "start_date": {"$lt": rental["end_date"]},
            "end_date": {"$gt": rental["start_date"]}
        })
        if conflict:
            flash("Cannot update status: Dates conflict with an existing booking.", "danger")
            return redirect(url_for("admin.rentals_list"))

    rentals_col.update_one(
        {"_id": rental["_id"]},
        {"$set": {"status": new_status}},
    )
    flash(f"Rental status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.rentals_list"))


# User Directory
@admin_bp.route("/users")
@login_required
@role_required("admin")
def users_list():
    """List registered users and activity counts."""
    users = list(users_col.find().sort("created_at", -1))
    for u in users:
        u["order_count"] = orders_col.count_documents({"user_id": u["_id"]})
        u["rental_count"] = rentals_col.count_documents({"user_id": u["_id"]})
    return render_template("admin/users.html", users=users)