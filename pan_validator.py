import re

def validate_pan(pan: str) -> bool:
    """
    Validates Indian PAN format: 5 letters + 4 digits + 1 letter
    """
    if not pan:
        return False
    return bool(re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan.upper()))
