"""User session model for Flask-Login."""

from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, doc: dict):
        self.id = str(doc["_id"])
        self.email = doc["email"]
        self.name = doc["name"]
        self.role = doc["role"]
        self.password_hash = doc["password_hash"]