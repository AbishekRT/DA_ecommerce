"""
auth/decorators.py
Custom Role-Based Access Control (RBAC) decorator.
Checks current_user.role (loaded from MongoDB via user_loader)
and aborts with 403 Forbidden if the user's role is not in the allowed roles.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """
    Usage:
        @role_required("admin")
        @role_required("admin", "staff")

    Protects routes based on one or more allowed user roles.
    Returns 403 Forbidden for any authenticated user without the specified role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator