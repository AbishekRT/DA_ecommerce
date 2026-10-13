"""Role-based access control decorator."""

from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Restricts view access to users with one of the allowed roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator