"""Authentication and user account management routes."""

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
    """Validate password length and character requirements."""
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


# Register
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("customer.catalog"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Required fields check
        if not name:
            flash("Full Name is required.", "danger")
            return render_template("auth/register.html")
        if not email:
            flash("Email address is required.", "danger")
            return render_template("auth/register.html")
        if not password:
            flash("Password is required.", "danger")
            return render_template("auth/register.html")

        # Format and matching checks
        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address (e.g. name@example.com).", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter identical passwords.", "danger")
            return render_template("auth/register.html")

        pw_errors = _validate_password(password, name)
        if pw_errors:
            for err in pw_errors:
                flash(err, "danger")
            return render_template("auth/register.html")

        # Ensure email is not already registered
        existing = users_col.find_one({"email": email})
        if existing:
            flash("An account with that email already exists. Please sign in or use another email.", "danger")
            return render_template("auth/register.html")

        new_user = {
            "email": email,
            "password_hash": generate_password_hash(password),
            "name": name,
            "role": "customer",
            "created_at": datetime.now(timezone.utc),
        }
        result = users_col.insert_one(new_user)
        new_user["_id"] = result.inserted_id

        user_obj = User(new_user)
        login_user(user_obj)
        flash("Account created successfully! Welcome to ProjectorShop.", "success")
        return redirect(url_for("customer.catalog"))

    return render_template("auth/register.html")


# Login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "staff":
            return redirect(url_for("admin.rentals_list"))
        return redirect(url_for("customer.catalog"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email:
            flash("Email address is required.", "danger")
            return render_template("auth/login.html")
        if not password:
            flash("Password is required.", "danger")
            return render_template("auth/login.html")

        if not EMAIL_REGEX.match(email):
            flash("Please enter a valid email address format (e.g. name@example.com).", "danger")
            return render_template("auth/login.html")

        doc = users_col.find_one({"email": email})
        if not doc:
            flash("No account found with this email address. Please check your spelling or register.", "danger")
            return render_template("auth/login.html")

        if not check_password_hash(doc["password_hash"], password):
            flash("Incorrect password entered. Please check your credentials.", "danger")
            return render_template("auth/login.html")

        user_obj = User(doc)
        login_user(user_obj)

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


# Logout
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("customer.catalog"))