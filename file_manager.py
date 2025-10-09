import os
import json
import shutil
from datetime import datetime

BASE_DIR = "clients"

def ensure_base_dir():
    os.makedirs(BASE_DIR, exist_ok=True)

def get_client_dir(client_id):
    return os.path.join(BASE_DIR, f"client_{client_id}")

def save_form16_pdf(client_id, pdf_file):
    ensure_base_dir()
    client_dir = get_client_dir(client_id)
    os.makedirs(client_dir, exist_ok=True)
    pdf_path = os.path.join(client_dir, "form16.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.read())
    return pdf_path

def save_extracted_data(client_id, data):
    client_dir = get_client_dir(client_id)
    json_path = os.path.join(client_dir, "extracted.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return json_path

def load_extracted_data(client_id):
    json_path = os.path.join(get_client_dir(client_id), "extracted.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def list_all_clients():
    ensure_base_dir()
    client_ids = []
    for name in os.listdir(BASE_DIR):
        if name.startswith("client_"):
            client_ids.append(name.replace("client_", ""))
    return sorted(client_ids)

def delete_client(client_id):
    client_dir = get_client_dir(client_id)
    if os.path.exists(client_dir):
        shutil.rmtree(client_dir)

def get_form16_path(client_id):
    path = os.path.join(get_client_dir(client_id), "form16.pdf")
    return path if os.path.exists(path) else None

def get_extracted_path(client_id):
    path = os.path.join(get_client_dir(client_id), "extracted.json")
    return path if os.path.exists(path) else None

def generate_client_id():
    return datetime.now().strftime("%Y%m%d%H%M%S")
