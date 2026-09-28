import os
import threading
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from waitress import serve

from collector_playwright import collect_option_chain
from db import connect, init_db

load_dotenv()
app = Flask(__name__)
collection_lock = threading.Lock()


def require_api_key(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        expected = os.getenv("API_KEY", "")
        if expected and request.headers.get("X-API-Key") != expected:
            return jsonify({"error": "Unauthorized"}), 401
        return handler(*args, **kwargs)
    return wrapped


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/collect")
@require_api_key
def collect():
    body = request.get_json(silent=True) or {}
    center = int(body.get("center", 0))
    expiry = str(body.get("expiry", "")).strip().upper()
    step = int(body.get("step", 100))
    sides = 5
    if center <= 0 or not expiry or step <= 0:
        return jsonify({"error": "Provide center, expiry and step > 0"}), 400
    if not collection_lock.acquire(blocking=False):
        return jsonify({"error": "Collection already running"}), 409
    try:
        return jsonify(collect_option_chain(center, expiry, step, sides))
    finally:
        collection_lock.release()


@app.get("/api/option-chain/latest")
@require_api_key
def latest():
    with connect() as conn:
        run = conn.execute(
            "SELECT * FROM collection_runs WHERE status='completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not run:
            return jsonify({"run": None, "rows": []})
        rows = conn.execute(
            "SELECT * FROM option_snapshots WHERE run_id=? ORDER BY strike,option_type",
            (run["id"],),
        ).fetchall()
    return jsonify({"run": dict(run), "rows": [dict(row) for row in rows]})


@app.get("/api/runs")
@require_api_key
def runs():
    limit = min(max(int(request.args.get("limit", 20)), 1), 200)
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM collection_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/runs/<int:run_id>")
@require_api_key
def run_details(run_id):
    with connect() as conn:
        run = conn.execute("SELECT * FROM collection_runs WHERE id=?", (run_id,)).fetchone()
        rows = conn.execute(
            "SELECT * FROM option_snapshots WHERE run_id=? ORDER BY strike,option_type",
            (run_id,),
        ).fetchall()
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify({"run": dict(run), "rows": [dict(row) for row in rows]})


if __name__ == "__main__":
    init_db()
    serve(app, host=os.getenv("API_HOST", "0.0.0.0"), port=int(os.getenv("API_PORT", "5050")))
