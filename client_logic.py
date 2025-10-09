# client_logic.py

import os
import json
import uuid
from datetime import datetime

CLIENTS_DIR = "clients"
METADATA_FILE = os.path.join(CLIENTS_DIR, "clients_metadata.json")

def ensure_client_folder():
    """Ensure clients folder and metadata file exist."""
    os.makedirs(CLIENTS_DIR, exist_ok=True)
    if not os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "w") as f:
            json.dump([], f, indent=2)

def generate_client_id(name, pan):
    """Generate a unique client ID."""
    return f"{name.replace(' ', '').lower()}_{pan.lower()}_{str(uuid.uuid4())[:8]}"

def add_client(name, pan, year):
    """Add a new client to metadata and create folder."""
    ensure_client_folder()
    client_id = generate_client_id(name, pan)
    client_folder = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_folder, exist_ok=True)

    client_data = {
        "client_id": client_id,
        "name": name,
        "pan": pan,
        "year": year,
        "created_at": datetime.now().isoformat()
    }

    metadata = load_all_clients()
    metadata.append(client_data)

    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

    return client_data

def load_all_clients():
    """Load all client metadata."""
    ensure_client_folder()
    if not os.path.exists(METADATA_FILE):
        return []
    with open(METADATA_FILE, "r") as f:
        return json.load(f)
