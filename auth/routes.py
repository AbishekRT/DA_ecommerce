"""
auth/routes.py
Authentication routes: register, login, logout, and staff/admin routing.
Includes specific error feedback, RFC-compliant email validation, and strict password security.
"""

import re
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import users_col
from models import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validate_password(password: str, name: str = "") -> list:
    """
    Academic & Production Grade Password Security Policy Validator:
      - Minimum 10 characters
      - At least one uppercase letter (A-Z)
      - At least one lowercase letter (a-z)
      - At least one decimal digit (0-9)
      - At least one special symbol (!@#$%^&*...)
      - Prohibits common trivial words ('password')
      - Prohibits containing the user's own name
    """
    errors = []
    if len(password) < 10:
        errors.append("Password must be at least 10 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one numeric digit (0-9).")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\",.<>?/\\|`~]", password):
        errors.append("Password must contain at least one special symbol (e.g. !@#$%^&*).")
    if "password" in password.lower():
        errors.append("Password cannot contain the common dictionary word 'password'.")
    if name and len(name.strip()) >= 3 and name.strip().lower() in password.lower():
        errors.append("Password cannot contain your personal name for security.")
    return errors


# ---------------------------------------------------------------------------
# Register (Customer Self-Registration)
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("customer.catalog"))

    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip().lower()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # 1. Check required fields
        if not name:
            flash("Full Name is required.", "danger")
            return render_template("auth/register.html")
        if not email:
            flash("Email address is required.", "danger")
            return render_template("auth/register.html")
        if not password:
            flash("Password is required.", "danger")
            return render_template("auth/register.html")

        # 2. Email format validation
        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address (e.g. name@example.com).", "danger")
            return render_template("auth/register.html")

        # 3. Confirm password match
        if password != confirm_password:
            flash("Passwords do not match. Please re-enter identical passwords.", "danger")
            return render_template("auth/register.html")

        # 4. Comprehensive password policy validation
        pw_errors = _validate_password(password, name)
        if pw_errors:
            for err in pw_errors:
                flash(err, "danger")
            return render_template("auth/register.html")

        # 5. Check for duplicate email (PyMongo find_one hits unique index)
        existing = users_col.find_one({"email": email})
        if existing:
            flash("An account with that email already exists. Please sign in or use another email.", "danger")
            return render_template("auth/register.html")

        # 6. Insert new user document with hashed password
        new_user = {
            "email":         email,
            "password_hash": generate_password_hash(password),
            "name":          name,
            "role":          "customer",   # Self-registered accounts are customers
            "created_at":    datetime.now(timezone.utc),
        }
        result = users_col.insert_one(new_user)
        new_user["_id"] = result.inserted_id

        # Log in newly registered user
        user_obj = User(new_user)
        login_user(user_obj)
        flash("Account created successfully! Welcome to ProjectorShop.", "success")
        return redirect(url_for("customer.catalog"))

    return render_template("auth/register.html")


# ---------------------------------------------------------------------------
# Login (Unified RBAC Authentication with Specific Errors)
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "staff":
            return redirect(url_for("admin.rentals_list"))
        return redirect(url_for("customer.catalog"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # 1. Validation for empty inputs
        if not email:
            flash("Email address is required.", "danger")
            return render_template("auth/login.html")
        if not password:
            flash("Password is required.", "danger")
            return render_template("auth/login.html")

        # 2. Email format validation
        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address format (e.g. name@example.com).", "danger")
            return render_template("auth/login.html")

        # 3. User lookup in MongoDB
        doc = users_col.find_one({"email": email})
        if not doc:
            flash("No account found with this email address. Please check your spelling or register.", "danger")
            return render_template("auth/login.html")

        # 4. Password check
        if not check_password_hash(doc["password_hash"], password):
            flash("Incorrect password entered. Please check your credentials.", "danger")
            return render_template("auth/login.html")

        # 5. Successful login
        user_obj = User(doc)
        login_user(user_obj)
        
        # Smart Role Routing
        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        
        if user_obj.role == "admin":
            flash(f"Welcome to Administration Portal, {user_obj.name}.", "success")
            return redirect(url_for("admin.dashboard"))
        elif user_obj.role == "staff":
            flash(f"Welcome to Operations Portal, {user_obj.name}.", "success")
            return redirect(url_for("admin.rentals_list"))
        else:
            flash(f"Welcome back, {user_obj.name}!", "success")
            return redirect(url_for("customer.catalog"))

    return render_template("auth/login.html")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("customer.catalog"))