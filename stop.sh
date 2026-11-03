#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Stop Instagram Automator and Release Android Wake Lock
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "bot.pid" ]; then
    PID=$(cat bot.pid)
    echo "Stopping Instagram Automator process (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    sleep 2
    if kill -0 "$PID" 2>/dev/null; then
        echo "Process did not exit, forcing kill..."
        kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f bot.pid
    echo "✅ Automator process stopped."
else
    echo "No bot.pid found. Attempting pkill..."
    pkill -f "python main.py" 2>/dev/null || true
    echo "Done."
fi

# Release wake lock
if command -v termux-wake-unlock &> /dev/null; then
    echo "🔓 Releasing Android wake-lock..."
    termux-wake-unlock
fi

echo "All services halted."
