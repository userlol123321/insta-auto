#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Start Instagram Automator with Android Wake Lock & Background Supervision
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Acquire Android Wake Lock so CPU doesn't sleep when screen turns off
if command -v termux-wake-lock &> /dev/null; then
    echo "🔒 Acquiring Android CPU wake-lock (prevents sleep)..."
    termux-wake-lock
fi

# 2. Activate virtual environment if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 3. Check if already running
if [ -f "bot.pid" ]; then
    OLD_PID=$(cat bot.pid)
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "⚠️ Bot is already running with PID $OLD_PID."
        echo "Visit http://localhost:8080 in Chrome or run ./stop.sh to terminate it."
        exit 0
    else
        rm -f bot.pid
    fi
fi

# 4. Start Web UI + Bot Service in background with nohup
echo "🚀 Launching Instagram Automator in background..."
nohup python main.py --web > bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > bot.pid

echo "✅ Bot started successfully! (PID: $BOT_PID)"
echo "📱 Open in your Android browser: http://localhost:8080"
echo "📜 View live logs with: tail -f bot.log"
echo "⏹️ To stop the bot anytime, run: ./stop.sh"
