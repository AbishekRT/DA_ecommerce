"""
app.py
Flask application factory with registered Blueprints and Custom Error Handlers (403, 404, 500).
"""

from flask import Flask, render_template
from dotenv import load_dotenv
import os

load_dotenv()   # load .env before anything else

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-key")

    # ------------------------------------------------------------------
    # Initialise extensions
    # ------------------------------------------------------------------
    from extensions import login_manager
    login_manager.init_app(app)

    # User loader — Flask-Login calls this on every request to rebuild
    # current_user from the session cookie's stored user id.
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

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from auth.routes import auth_bp
    from customer.routes import customer_bp
    from admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ------------------------------------------------------------------
    # Custom Error Handlers (Industrial Grade 403, 404, 500 Pages)
    # ------------------------------------------------------------------
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

# Expose top-level application instance for Vercel / WSGI servers
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)