"""
backend_server.py
-----------------
Flask API server that bridges the solar panel dashboard (HTML/JS)
with the local LLM decision engine (Ollama + DeepSeek-R1).

Endpoints:
  GET  /api/sensor        → latest simulated sensor reading
  POST /api/decide        → run LLM on provided sensor data
  GET  /api/decide/auto   → get sensor data + run LLM in one call
  GET  /api/history       → last N LLM decisions
  GET  /api/health        → check server + Ollama status

Run:
  python backend_server.py

Then in your dashboard JS, call:
  http://localhost:5000/api/decide/auto
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import time
import threading

from data_generator import SolarSensorSimulator
from llm_decision_engine import SolarLLMDecisionEngine

# ── App setup ──────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allows your dashboard (Live Server) to call this API

# ── Globals ────────────────────────────────────────────────────────────────
simulator = SolarSensorSimulator()
engine = SolarLLMDecisionEngine(model_name="deepseek-r1")  # change to "mistral" if needed

# Cache latest sensor reading so dashboard can poll it without re-generating
_latest_sensor = None
_sensor_lock = threading.Lock()


def _refresh_sensor():
    """Background thread: updates sensor reading every 5 seconds."""
    global _latest_sensor
    while True:
        with _sensor_lock:
            _latest_sensor = simulator.generate()
        time.sleep(5)


# Start background sensor thread
sensor_thread = threading.Thread(target=_refresh_sensor, daemon=True)
sensor_thread.start()


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Check that the server and Ollama are reachable."""
    try:
        import ollama
        models = ollama.list()
        model_names = [m["name"] for m in models.get("models", [])]
        return jsonify({
            "status": "ok",
            "server": "running",
            "ollama": "connected",
            "available_models": model_names,
            "active_model": engine.model,
        })
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "server": "running",
            "ollama": f"error: {str(e)}",
        }), 500


@app.route("/api/sensor", methods=["GET"])
def get_sensor():
    """Return the latest simulated sensor reading."""
    with _sensor_lock:
        data = _latest_sensor or simulator.generate()
    return jsonify({"success": True, "data": data})


@app.route("/api/decide", methods=["POST"])
def decide_from_payload():
    """
    Run LLM decision on sensor data sent in the request body.
    Useful when your real sensors push data to the backend.

    Body (JSON):
      { "wind_speed": 12.5, "dust_level": 35.0, "battery_pct": 72.0, ... }
    """
    sensor_data = request.get_json(force=True)
    if not sensor_data:
        return jsonify({"success": False, "error": "No sensor data provided"}), 400

    result = engine.decide(sensor_data)
    return jsonify(result)


@app.route("/api/decide/auto", methods=["GET"])
def decide_auto():
    """
    One-shot endpoint: grabs the latest sensor reading and runs the LLM on it.
    Your dashboard should call this endpoint when the user clicks 'Analyze Now'.
    """
    with _sensor_lock:
        sensor_data = _latest_sensor or simulator.generate()

    result = engine.decide(sensor_data)
    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def get_history():
    """Return the last N LLM decisions."""
    history = engine.get_history()
    return jsonify({"success": True, "history": history, "count": len(history)})


@app.route("/api/model", methods=["POST"])
def switch_model():
    """
    Switch the active LLM model at runtime.
    Body: { "model": "mistral" }
    """
    body = request.get_json(force=True)
    new_model = body.get("model")
    if not new_model:
        return jsonify({"success": False, "error": "model name required"}), 400

    engine.model = new_model
    return jsonify({"success": True, "model": engine.model})


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  SolarWinds LLM Backend")
    print("  Model    :", engine.model)
    print("  API Base : http://localhost:5000")
    print("  Endpoints:")
    print("    GET  /api/health")
    print("    GET  /api/sensor")
    print("    GET  /api/decide/auto   ← dashboard uses this")
    print("    POST /api/decide")
    print("    GET  /api/history")
    print("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=True)
