#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        CritiqueFlow v1.0             ║"
echo "║        Audit Harness                 ║"
echo "╚══════════════════════════════════════╝"
echo ""

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
else
    echo "ERROR: Python venv not found at .venv/"
    echo "Run: uv venv && uv pip install -r requirements.txt"
    exit 1
fi

rm -f .port

python run.py &
SERVER_PID=$!

WAITED=0
while [ ! -f ".port" ] && [ $WAITED -lt 20 ]; do
    sleep 0.5
    WAITED=$((WAITED + 1))
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "ERROR: Server failed to start"
        exit 1
    fi
done

if [ ! -f ".port" ]; then
    echo "ERROR: Server did not write .port file within 10 seconds"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

PORT=$(cat .port)
URL="http://127.0.0.1:${PORT}"

echo "✓ CritiqueFlow running at ${URL}"
echo "  Press Ctrl+C to stop"
echo ""

if command -v xdg-open &>/dev/null; then
    xdg-open "$URL" 2>/dev/null &
elif command -v open &>/dev/null; then
    open "$URL" &
elif command -v start &>/dev/null; then
    start "$URL" &
fi

cleanup() {
    echo ""
    echo "Shutting down CritiqueFlow..."
    kill $SERVER_PID 2>/dev/null
    rm -f .port
    exit 0
}
trap cleanup SIGINT SIGTERM

wait $SERVER_PID
