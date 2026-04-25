"""
EdgeNode – HIL Integration Test
================================
End-to-end test that triggers a fault on the edge-node server and
optically verifies the smartphone screen turns red via the webcam.

Prerequisites
-------------
* The Flask server (``src/server.py``) must be running on localhost:5000.
* A webcam must be pointed at the smartphone displaying the status page.
"""

import sys
import os

import pytest
import requests

# Ensure the project root is on the path so we can import src.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cv_validator import verify_hardware_color

BASE_URL = "http://localhost:5000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_node_state() -> None:
    """Return the node to NOMINAL before / after tests."""
    requests.post(f"{BASE_URL}/api/resolve_fault", timeout=5)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state():
    """Ensure the node starts and ends each test in NOMINAL."""
    _reset_node_state()
    yield
    _reset_node_state()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHILExecution:
    """Hardware-in-the-loop integration tests."""

    def test_trigger_fault_shows_red(self):
        """After triggering a fault the phone screen must turn red."""
        # 1. Trigger the fault via REST API
        resp = requests.post(
            f"{BASE_URL}/api/trigger_fault",
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "FAULT"

        # 2. Give the browser polling loop time to update the colour
        import time
        time.sleep(1)

        # 3. Optically verify the screen is now RED
        assert verify_hardware_color(target_color="RED", duration=2) is True

    def test_resolve_fault_shows_green(self):
        """After resolving a fault the phone screen must turn green."""
        # First trigger a fault …
        requests.post(f"{BASE_URL}/api/trigger_fault", timeout=5)
        import time
        time.sleep(1)

        # … then resolve it
        resp = requests.post(
            f"{BASE_URL}/api/resolve_fault",
            timeout=5,
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "NOMINAL"

        time.sleep(1)

        # Optically verify green
        assert verify_hardware_color(target_color="GREEN", duration=2) is True

    def test_get_state_returns_nominal_by_default(self):
        """The default node state should be NOMINAL."""
        resp = requests.get(f"{BASE_URL}/api/state", timeout=5)
        assert resp.status_code == 200
        assert resp.json()["state"] == "NOMINAL"
