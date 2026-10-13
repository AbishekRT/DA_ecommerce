"""Flask application factory and configuration."""

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv
import os

load_dotenv()

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-key")

    # Initialize extensions
    csrf.init_app(app)

    from extensions import login_manager
    login_manager.init_app(app)

    # Reload user instance from session cookie
    from extensions import users_col
    from bson import ObjectId
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            doc = users_col.find_one({"_id": ObjectId(user_id)})
            if doc:
                return User(doc)
        except Exception:
            return None
        return None

    # Register blueprints
    from auth.routes import auth_bp
    from customer.routes import customer_bp
    from admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Inject cart count into customer navbar
    @app.context_processor
    def inject_cart_count():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.role == 'customer':
            try:
                from extensions import carts_col
                cart = carts_col.find_one({"user_id": ObjectId(current_user.id)})
                count = len(cart.get("items", [])) if cart else 0
                return dict(cart_count=count)
            except Exception:
                return dict(cart_count=0)
        return dict(cart_count=0)

    @app.template_filter('clean_dash')
    def clean_dash_filter(s):
        if not s:
            return ""
        return str(s).replace('\u2014', ' - ').replace('\u2013', ' - ').replace('&mdash;', ' - ').replace('&ndash;', ' - ')

    # Error handlers
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("Your security session expired or the form submission was invalid. Please try again.", "danger")
        return redirect(request.referrer or url_for("customer.catalog"))

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("500.html"), 500

    return app


# WSGI application entry point
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)