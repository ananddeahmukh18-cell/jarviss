#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  JARVIS — Smart Launcher (USB Portable)
#
#  Works on ANY Mac — first run auto-installs everything.
#  Subsequent runs start in under 2 seconds.
#
#  Usage:
#    bash run.sh          → Terminal mode (chat in this window)
#    bash run.sh bot      → iPhone/Telegram mode
#    bash run.sh clean    → Remove venv (reset for fresh install)
# ═══════════════════════════════════════════════════════════════════

set -e
B="\033[1m"; C="\033[36m"; G="\033[32m"; Y="\033[33m"; R="\033[31m"; X="\033[0m"

# Always run from the folder this script lives in (works from USB)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ── Clean flag ────────────────────────────────────────────────────
if [ "$1" = "clean" ]; then
    echo -e "${Y}  Removing venv and cache …${X}"
    rm -rf venv __pycache__ tools/__pycache__
    find . -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${G}  ✔  Cleaned. Run again to reinstall fresh.${X}"
    exit 0
fi

echo -e "\n${C}${B}"
echo "     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗"
echo "     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝"
echo "     ██║███████║██████╔╝██║   ██║██║███████╗"
echo "██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║"
echo "╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║"
echo " ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝"
echo -e "${X}"

# ── Python check ──────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${R}  ✘  Python 3 not found!${X}"
    echo -e "  Download from: https://python.org/downloads"
    exit 1
fi
PY=$(python3 --version | awk '{print $2}')
MINOR=$(echo "$PY" | cut -d. -f2)
if [ "$MINOR" -lt 10 ]; then
    echo -e "${R}  ✘  Need Python 3.10+, found $PY. Update from python.org${X}"
    exit 1
fi

# ── Auto-install on first run or new device ────────────────────────
if [ ! -d "venv" ] || [ ! -f "venv/bin/python" ]; then
    echo -e "${Y}  First run on this device — installing JARVIS …${X}\n"

    python3 -m venv venv
    source venv/bin/activate

    pip install -q --upgrade pip

    # Core — always required
    pip install -q openai "python-telegram-bot>=20.0" python-dotenv
    pip install -q rich requests psutil Pillow duckduckgo-search pyperclip colorama
    echo -e "${G}  ✔  Core packages installed${X}"

    # Voice — optional
    pip install -q pyttsx3          2>/dev/null && echo -e "${G}  ✔  pyttsx3 (TTS)${X}"         || echo -e "${Y}  ⚠  pyttsx3 skipped${X}"
    pip install -q SpeechRecognition 2>/dev/null && echo -e "${G}  ✔  SpeechRecognition${X}"    || echo -e "${Y}  ⚠  SpeechRecognition skipped${X}"

    # PyAudio needs portaudio (Homebrew)
    if command -v brew &>/dev/null; then
        brew install portaudio -q 2>/dev/null || true
        pip install -q pyaudio 2>/dev/null    && echo -e "${G}  ✔  PyAudio (microphone)${X}"  || echo -e "${Y}  ⚠  PyAudio skipped${X}"
    else
        echo -e "${Y}  ⚠  Homebrew not found — microphone input disabled${X}"
        echo -e "     Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi

    # Screenshot / keyboard automation
    pip install -q pyautogui 2>/dev/null      && echo -e "${G}  ✔  pyautogui (screenshot/typing)${X}" || echo -e "${Y}  ⚠  pyautogui skipped${X}"

    echo -e "\n${G}${B}  ✔  Installation complete!${X}\n"
else
    source venv/bin/activate
fi

# ── Launch ────────────────────────────────────────────────────────
if [ "$1" = "bot" ]; then
    echo -e "${B}  📱  Starting iPhone / Telegram mode …${X}\n"
    python bot.py
else
    echo -e "${B}  🚀  Starting terminal mode …${X}\n"
    python main.py
fi
