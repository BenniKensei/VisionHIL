"""
EdgeNode – Smartphone Edge Node Simulator
==========================================
A lightweight Flask server that simulates a smartphone edge node.
The served HTML page polls the node state every 500ms and sets the
background colour to **green** (NOMINAL) or **red** (FAULT).
"""

import os

from flask import Flask, jsonify, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Global node state
# ---------------------------------------------------------------------------
NODE_STATE: str = "NOMINAL"

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the live-polling status page."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EdgeNode Status</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', system-ui, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                transition: background-color 0.3s ease;
                background-color: #22c55e; /* default green */
            }
            #status {
                font-size: 6rem;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.9);
                text-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
                letter-spacing: 0.05em;
                user-select: none;
            }
        </style>
    </head>
    <body>
        <div id="status">NOMINAL</div>
        <script>
            async function poll() {
                try {
                    const res  = await fetch('/api/state');
                    const data = await res.json();
                    const state = data.state;

                    document.getElementById('status').textContent = state;

                    if (state === 'NOMINAL') {
                        document.body.style.backgroundColor = '#22c55e';
                    } else if (state === 'FAULT') {
                        document.body.style.backgroundColor = '#ef4444';
                    }
                } catch (err) {
                    console.error('Poll error:', err);
                }
            }
            setInterval(poll, 500);
            poll();
        </script>
    </body>
    </html>
    """


@app.route("/api/state", methods=["GET"])
def get_state():
    """Return the current node state as JSON."""
    return jsonify({"state": NODE_STATE})


@app.route("/api/trigger_fault", methods=["POST"])
def trigger_fault():
    """Transition the node into the FAULT state."""
    global NODE_STATE
    NODE_STATE = "FAULT"
    return jsonify({"state": NODE_STATE})


@app.route("/api/resolve_fault", methods=["POST"])
def resolve_fault():
    """Transition the node back to NOMINAL."""
    global NODE_STATE
    NODE_STATE = "NOMINAL"
    return jsonify({"state": NODE_STATE})


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Clear any inherited reloader flag when the server is started directly.
    # On Windows, Werkzeug can otherwise try to read WERKZEUG_SERVER_FD and fail.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" and "WERKZEUG_SERVER_FD" not in os.environ:
        os.environ.pop("WERKZEUG_RUN_MAIN", None)

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
