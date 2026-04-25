#!/bin/bash
# ---------------------------------------------------------------------------
# VisionHIL – Phase 2 Orchestration Script
# ---------------------------------------------------------------------------
# Launches the Flask edge-node server, waits for it to become healthy,
# runs the pytest HIL suite, then tears everything down.
# Designed for Git Bash on Windows; POSIX-compatible.
# ---------------------------------------------------------------------------

set -euo pipefail

SERVER_CMD="python src/server.py"
HEALTH_URL="http://localhost:5000/api/state"
HEALTH_TIMEOUT=10          # max seconds to wait for the server
HEALTH_INTERVAL=1          # seconds between health-check retries
SERVER_PID=""

# ---------------------------------------------------------------------------
# cleanup – kill the background Flask process.
# Registered via trap so it fires on EXIT, SIGINT (Ctrl+C), and SIGTERM,
# preventing zombie processes from holding port 5000.
# ---------------------------------------------------------------------------
cleanup() {
    if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
        echo "[teardown] Killing edge-node server (PID ${SERVER_PID})..."
        kill "${SERVER_PID}" 2>/dev/null
        wait "${SERVER_PID}" 2>/dev/null || true
    fi
}

trap cleanup EXIT SIGINT SIGTERM

# ---------------------------------------------------------------------------
# 1. Start the Flask server in the background and capture its PID.
# ---------------------------------------------------------------------------
echo "[init] Starting edge-node server..."
${SERVER_CMD} &
SERVER_PID=$!
echo "[init] Server launched (PID ${SERVER_PID})."

# ---------------------------------------------------------------------------
# 2. Health-check polling loop.
#    Uses curl -s -o /dev/null -w "%{http_code}" to extract the HTTP status
#    code without printing the response body. Retries every HEALTH_INTERVAL
#    seconds up to HEALTH_TIMEOUT.
# ---------------------------------------------------------------------------
echo "[health] Waiting for edge node to initialize..."
elapsed=0

while (( elapsed < HEALTH_TIMEOUT )); do
    # curl exits 0 on any HTTP response; -f would exit non-zero on 4xx/5xx.
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null || echo "000")

    if [[ "${http_code}" == "200" ]]; then
        echo "[health] Edge node is healthy (HTTP ${http_code})."
        break
    fi

    echo "[health] Not ready (HTTP ${http_code}). Retrying in ${HEALTH_INTERVAL}s..."
    sleep "${HEALTH_INTERVAL}"
    (( elapsed += HEALTH_INTERVAL ))
done

if (( elapsed >= HEALTH_TIMEOUT )); then
    echo "[health] ERROR: Server failed to become healthy within ${HEALTH_TIMEOUT}s."
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Execute the pytest HIL suite and capture its exit code.
#    +e temporarily disables errexit so a test failure doesn't skip teardown.
# ---------------------------------------------------------------------------
echo "[test] Running HIL test suite..."
set +e
pytest -v tests/
TEST_EXIT_CODE=$?
set -e

# ---------------------------------------------------------------------------
# 4. Teardown & propagate the pytest exit code.
#    cleanup is called explicitly here (and also by the EXIT trap as a
#    safety net). The script exits with pytest's code so CI/CD pipelines
#    correctly register pass/fail.
# ---------------------------------------------------------------------------
cleanup
exit "${TEST_EXIT_CODE}"
