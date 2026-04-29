# routes/utils.py
import re

# نمط البريد الإلكتروني
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def is_valid_email(email: str) -> bool:
    """Validate email format."""
    return bool(re.match(EMAIL_PATTERN, email))

def validate_password(password: str) -> tuple:
    """
    Validate password strength.
    Returns (is_valid, message)
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    # optional: special character check
    # if not any(c in "!@#$%^&*" for c in password):
    #     return False, "Password must contain at least one special character"
    return True, "Password is valid"