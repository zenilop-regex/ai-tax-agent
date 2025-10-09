import os
import json
import uuid
import re
from datetime import datetime

CLIENTS_FILE = "clients.json"

def load_clients():
    """Load all clients from JSON file"""
    if not os.path.exists(CLIENTS_FILE):
        return []
    with open(CLIENTS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_clients(clients):
    """Save clients to JSON file"""
    with open(CLIENTS_FILE, "w") as f:
        json.dump(clients, f, indent=4)

def generate_client_id(name, pan):
    """Generate unique client ID"""
    unique_id = str(uuid.uuid4())[:8]
    return f"{name.lower().replace(' ', '')}_{pan.upper()}_{unique_id}"

def verify_pan(pan):
    """Validate PAN format"""
    if not pan:
        return False
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan.upper()))

def get_client_by_pan(clients, pan):
    """Get client by PAN number"""
    return next((c for c in clients if c.get("pan", "").upper() == pan.upper()), None)

def get_client_by_id(clients, client_id):
    """Get client by ID"""
    return next((c for c in clients if c.get("client_id") == client_id), None)

# NOTE: apply_overrides function removed from here
# It should ONLY exist in itd_mapper.py to avoid conflicts
# Import it like: from itd_mapper import apply_overrides