"""
models.py
Minimal User class required by Flask-Login.
This is NOT an ODM model — it is a thin wrapper around a raw MongoDB
document (Python dict) purely to satisfy Flask-Login's interface.
All actual database reads/writes happen directly in route functions
using PyMongo calls.
"""

from flask_login import UserMixin


class User(UserMixin):
    """
    Wraps a raw MongoDB user document so Flask-Login can manage sessions.
    Attributes are read directly from the document dict — no schema magic.
    """

    def __init__(self, doc: dict):
        self.id   = str(doc["_id"])   # Flask-Login requires a string id
        self.email = doc["email"]
        self.name  = doc["name"]
        self.role  = doc["role"]       # "admin" or "customer"
        self.password_hash = doc["password_hash"]