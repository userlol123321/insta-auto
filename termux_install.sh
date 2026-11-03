#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Automated Instagram Bot - One-Step Termux Installer for Android
# ==============================================================================

set -e

echo "=========================================================="
echo " 📱 Setting up Instagram DM Automator in Termux (Android) "
echo "=========================================================="

echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "[2/5] Installing core build tools and dependencies..."
pkg install -y python python-pip clang make libffi openssl libxml2 libxslt termux-api

echo "[3/5] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
fi
source venv/bin/activate

echo "[4/5] Upgrading pip and wheel..."
pip install --upgrade pip wheel setuptools

echo "[5/5] Installing Python requirements (instagrapi, flask, etc.)..."
pip install -r requirements.txt

# Grant execute permissions to runner scripts
chmod +x start.sh stop.sh termux_install.sh

# Prepare config.yaml if it doesn't exist
if [ ! -f "config.yaml" ]; then
    cp config.yaml.example config.yaml
    echo "Created config.yaml from template."
fi

echo ""
echo "=========================================================="
echo " 🎉 Installation Complete!"
echo "=========================================================="
echo "Next Steps:"
echo "1. Edit your Instagram credentials in config.yaml:"
echo "   nano config.yaml"
echo ""
echo "2. Run the initial login to create your session (and handle 2FA/SMS):"
echo "   python main.py --login"
echo ""
echo "3. Start the bot 24/7 in background:"
echo "   ./start.sh"
echo ""
echo "4. Open http://localhost:8080 in Chrome on your Android phone to manage!"
echo "=========================================================="
