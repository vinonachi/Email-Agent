"""
storage.py

Saves processed inbox data to a local JSON file so a separate
dashboard process can read it without ever touching Gmail itself.
"""

import json
from datetime import datetime, timezone

DATA_FILE = "inbox_data.json"


def save_results(emails):
    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "emails": emails,
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_results():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"last_updated": None, "emails": []}
