
from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
from threading import Lock
import json
from datetime import datetime, timezone

app = Flask(__name__, static_folder="static")

DATA_FILE = Path(__file__).parent / "rsvp.json"
ADMIN_SLUG = "matrimonio-rsvp-control-7n4qk2"
write_lock = Lock()

VALID_STATUSES = {"pending", "yes", "no"}


def slugify(value):
    return "".join(
        character.lower() if character.isalnum() else "-"
        for character in value.strip()
    ).strip("-")


def load_rsvp_groups():
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_rsvp_groups(groups):
    DATA_FILE.parent.mkdir(exist_ok=True)
    temp_file = DATA_FILE.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2)
        f.write("\n")

    temp_file.replace(DATA_FILE)


def find_rsvp_group(groups, invite_name):
    requested = slugify(invite_name)
    for group in groups:
        if requested == slugify(group.get("id", "")):
            return group

    return None


def build_admin_summary(groups):
    totals = {status: 0 for status in VALID_STATUSES}
    totals["total"] = 0
    by_side = {}
    by_type = {}

    for group in groups:
        side = group.get("side") or "Unassigned"
        group_type = group.get("type") or "Unassigned"
        by_side.setdefault(side, {status: 0 for status in VALID_STATUSES})
        by_type.setdefault(group_type, {status: 0 for status in VALID_STATUSES})

        for guest in group.get("guests", []):
            status = guest.get("status", "pending")
            if status not in VALID_STATUSES:
                status = "pending"

            totals[status] += 1
            totals["total"] += 1
            by_side[side][status] += 1
            by_type[group_type][status] += 1

    return {
        "totals": totals,
        "by_side": by_side,
        "by_type": by_type,
        "groups": groups,
    }

def not_found_page():
    return send_from_directory("static", "404.html"), 404

@app.route("/")
def home():
    print("home")
    return send_from_directory("static", "index.html")

@app.route("/rsvp")
def rsvp_page():
    return send_from_directory("static", "rsvp.html")

@app.route("/rsvp/<path:invite_name>")
def named_rsvp_page(invite_name):
    if find_rsvp_group(load_rsvp_groups(), invite_name) is None:
        return not_found_page()

    return send_from_directory("static", "rsvp.html")

@app.route(f"/{ADMIN_SLUG}")
def admin_page():
    return send_from_directory("private", "admin.html")

@app.route(f"/api/{ADMIN_SLUG}")
def admin_data():
    return jsonify(build_admin_summary(load_rsvp_groups()))

@app.route("/api/rsvp/<path:invite_name>", methods=["GET", "POST"])
def group_rsvp(invite_name):
    if request.method == "GET":
        groups = load_rsvp_groups()
        group = find_rsvp_group(groups, invite_name)
        if group is None:
            return jsonify(error="RSVP group not found"), 404

        return jsonify(group)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Invalid request"), 400

    submitted_guests = data.get("guests")
    dietary = data.get("dietary", "")

    if not isinstance(submitted_guests, list) or not isinstance(dietary, str):
        return jsonify(error="Invalid RSVP details"), 400

    statuses_by_name = {}
    for guest in submitted_guests:
        if not isinstance(guest, dict):
            return jsonify(error="Invalid guest details"), 400

        name = guest.get("name")
        status = guest.get("status")
        if (
            not isinstance(name, str)
            or not name.strip()
            or status not in VALID_STATUSES
        ):
            return jsonify(error="Invalid guest details"), 400

        statuses_by_name[name.strip()] = status

    with write_lock:
        groups = load_rsvp_groups()
        group = find_rsvp_group(groups, invite_name)
        if group is None:
            return jsonify(error="RSVP group not found"), 404

        known_names = {
            guest.get("name")
            for guest in group.get("guests", [])
            if isinstance(guest, dict)
        }
        if set(statuses_by_name) != known_names:
            return jsonify(error="Guest list does not match this RSVP group"), 400

        for guest in group.get("guests", []):
            guest["status"] = statuses_by_name[guest["name"]]

        group["dietary"] = dietary.strip()
        group["submitted_at"] = datetime.now(timezone.utc).isoformat()
        save_rsvp_groups(groups)

    return jsonify(message="RSVP saved successfully", group=group), 200

@app.route("/api/rsvp", methods=["POST"])
def save_rsvp():
    return jsonify(error="Use a named RSVP link."), 400

@app.route("/<path:invite_name>")
def root_named_rsvp_page(invite_name):
    if find_rsvp_group(load_rsvp_groups(), invite_name) is None:
        return not_found_page()

    return send_from_directory("static", "index.html")

@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith("/api/"):
        return jsonify(error="Not found"), 404

    return not_found_page()

if __name__ == "__main__":
    app.run(host="::", port=5000, debug=True)
