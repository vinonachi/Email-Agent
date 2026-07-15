"""
app.py

Local Flask server for the Inbox Radar dashboard.
Run with:  python app.py
Then open: http://localhost:5000

Endpoints:
  GET  /              → serves the dashboard UI
  GET  /api/emails    → returns inbox_data.json contents
  POST /api/run       → runs run_agent.py to refresh inbox data
"""

import json
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template

app = Flask(__name__)

DATA_FILE = Path("inbox_data.json")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/emails")
def get_emails():
    if not DATA_FILE.exists():
        return jsonify({"last_updated": None, "emails": []})
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/run", methods=["POST"])
def run_agent():
    try:
        result = subprocess.run(
            [sys.executable, "run_agent.py"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return jsonify({"ok": False, "error": result.stderr}), 500
        return jsonify({"ok": True, "output": result.stdout})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Agent timed out after 60 seconds"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
