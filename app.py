
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
from threading import Lock
import json
import uuid
from datetime import datetime, timezone

app = Flask(__name__, static_folder="static")

DATA_FILE = Path(__file__).parent / "data" / "rsvps.json"
write_lock = Lock()

@app.route("/")
def home():
    print("home")
    return send_from_directory("static", "index.html")

@app.route("/rsvp")
def rsvp_page():
    print("rsvpppppp")
    return send_from_directory("static", "rsvp.html")

@app.route("/api/rsvp", methods=["POST"])
def save_rsvp():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Invalid request"), 400

    name = data.get("name")
    attending = data.get("attending")
    email = data.get("email", "")

    if (
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 150
        or attending not in ("yes", "no")
        or not isinstance(email, str)
        or len(email) > 254
    ):
        return jsonify(error="Invalid RSVP details"), 400

    entry = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "email": email.strip(),
        "attending": attending,
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }

    with write_lock:
        DATA_FILE.parent.mkdir(exist_ok=True)

        if DATA_FILE.exists():
            with DATA_FILE.open("r", encoding="utf-8") as f:
                rsvps = json.load(f)
        else:
            rsvps = []

        rsvps.append(entry)

        temp_file = DATA_FILE.with_suffix(".tmp")
        with temp_file.open("w", encoding="utf-8") as f:
            json.dump(rsvps, f, indent=2)

        temp_file.replace(DATA_FILE)

    return jsonify(message="RSVP saved successfully"), 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)
