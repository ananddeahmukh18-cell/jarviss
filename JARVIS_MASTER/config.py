"""
JARVIS Master Config — Portable Edition
All keys pre-filled. Works from USB on any Mac.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── OpenRouter API (FREE — no daily token limit) ──────────────────
OPENROUTER_API_KEY: str = os.getenv(
    "OPENROUTER_API_KEY",
    "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"
)
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# ── Models ────────────────────────────────────────────────────────
# Primary: OpenAI open-weight, best tool-calling, $0/token
MODEL_PRIMARY:  str = "openai/gpt-oss-20b:free"
# Fallback if primary rate-limited
MODEL_FALLBACK: str = "meta-llama/llama-3.3-70b-instruct:free"
# Vision: supports image input for analyze_screen tool
MODEL_VISION:   str = "meta-llama/llama-3.2-11b-vision-instruct:free"
# Shown in UI banner
MODEL: str = MODEL_PRIMARY
MAX_TOKENS: int = 2048

# ── Telegram (iPhone remote control) ─────────────────────────────
TELEGRAM_BOT_TOKEN:  str = os.getenv("TELEGRAM_BOT_TOKEN",  "8621721574:AAFFpT7HDIvt3bAyk8ivuM1Pqw3wrSTTerU")
TELEGRAM_ALLOWED_ID: str = os.getenv("TELEGRAM_ALLOWED_ID", "8674595113")

# ── Identity ──────────────────────────────────────────────────────
JARVIS_NAME: str = os.getenv("JARVIS_NAME", "JARVIS")

# ── Voice ─────────────────────────────────────────────────────────
# ALL vars required by voice_engine.py — must ALL be defined
VOICE_ENABLED: bool = os.getenv("VOICE_ENABLED", "false").lower() == "true"
TTS_RATE: int       = int(os.getenv("TTS_RATE",    "170"))
TTS_VOLUME: float   = float(os.getenv("TTS_VOLUME", "0.9"))
TTS_GENDER: str     = os.getenv("TTS_GENDER",      "male").lower()

# ── Safety ────────────────────────────────────────────────────────
# False = no confirmation prompts (needed for Telegram/remote mode)
CONFIRM_COMMANDS: bool = os.getenv("CONFIRM_COMMANDS", "false").lower() == "true"
CONFIRM_DELETE: bool   = os.getenv("CONFIRM_DELETE",   "false").lower() == "true"

# Set True by bot.py at runtime — skips all prompts for remote commands
REMOTE_MODE: bool = False

MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "20"))

# ── File organiser — FULL map (required by tools/file_manager.py) ─
FILE_TYPE_MAP: dict = {
    "Images":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                    ".webp", ".ico", ".tiff", ".heic", ".raw"],
    "Videos":      [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
                    ".webm", ".m4v", ".3gp"],
    "Audio":       [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
                    ".wma", ".opus", ".aiff"],
    "Documents":   [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx",
                    ".ppt", ".txt", ".rtf", ".odt", ".ods", ".odp",
                    ".csv", ".pages", ".numbers", ".key"],
    "Code":        [".py", ".js", ".ts", ".html", ".css", ".java",
                    ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php",
                    ".sh", ".bat", ".ps1", ".json", ".yaml", ".yml",
                    ".xml", ".sql", ".md", ".swift", ".kt", ".dart",
                    ".r", ".ipynb"],
    "Archives":    [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
                    ".xz", ".dmg", ".iso"],
    "Executables": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm",
                    ".appimage", ".app"],
    "Fonts":       [".ttf", ".otf", ".woff", ".woff2"],
    "ebooks":      [".epub", ".mobi", ".azw", ".azw3"],
    "3D":          [".obj", ".stl", ".fbx", ".blend", ".glb", ".gltf"],
}
