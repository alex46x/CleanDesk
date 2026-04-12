"""
config.py — Central configuration for Smart File Organizer AI
All tunable constants live here; environment variables override defaults.
"""

import os
import sys
import platform
from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "smart_organizer.db"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# SQLite by default; swap to PostgreSQL DSN via env var for production
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{DB_PATH}",
)

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("API_PORT", "8765"))
API_RELOAD: bool = os.getenv("API_RELOAD", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Scanner behaviour
# ---------------------------------------------------------------------------
SCAN_MAX_WORKERS: int = int(os.getenv("SCAN_MAX_WORKERS", str(os.cpu_count() or 4)))
SCAN_QUEUE_SIZE: int = 10_000          # bounded queue to cap memory
SCAN_CHUNK_SIZE: int = 512            # directories processed per worker batch

# ---------------------------------------------------------------------------
# File mover
# ---------------------------------------------------------------------------
COPY_BUFFER_SIZE: int = 4 * 1024 * 1024   # 4 MB buffer for cross-drive copies
MAX_FILENAME_COLLISIONS: int = 999         # rename suffixes before error

# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------
# Hash only files larger than this (skip tiny files → pure size compare)
HASH_MIN_SIZE: int = 1024   # 1 KB
HASH_CHUNK_SIZE: int = 8 * 1024 * 1024   # 8 MB read chunk for hashing

# ---------------------------------------------------------------------------
# Safety — protected directories (NEVER touched)
# ---------------------------------------------------------------------------
_WINDOWS_PROTECTED = {
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\System Volume Information",
    "C:\\$Recycle.Bin",
    "C:\\Recovery",
    "C:\\Boot",
}

_UNIX_PROTECTED = {
    "/bin", "/sbin", "/usr/bin", "/usr/sbin",
    "/etc", "/lib", "/lib64", "/proc", "/sys",
    "/dev", "/run", "/boot", "/root",
}

PROTECTED_PATHS: set[str] = (
    _WINDOWS_PROTECTED if platform.system() == "Windows" else _UNIX_PROTECTED
)

# ---------------------------------------------------------------------------
# Classification — default rules
# ---------------------------------------------------------------------------
CATEGORY_RULES: dict[str, list[str]] = {
    "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                   ".webp", ".tiff", ".tif", ".heic", ".raw", ".cr2", ".nef"],
    "Videos":     [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
                   ".webm", ".m4v", ".3gp", ".ts", ".m2ts"],
    "Audio":      [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
                   ".wma", ".opus", ".aiff"],
    "Documents":  [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
                   ".pptx", ".odt", ".ods", ".txt", ".rtf", ".md",
                   ".csv", ".epub"],
    "Archives":   [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
                   ".xz", ".iso", ".dmg"],
    "Code":       [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
                   ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs",
                   ".rb", ".php", ".swift", ".kt", ".sql", ".sh",
                   ".bat", ".ps1", ".json", ".yaml", ".yml", ".toml",
                   ".xml", ".ini", ".cfg", ".env"],
    "Executables":[".exe", ".msi", ".apk", ".app", ".deb", ".rpm"],
    "Fonts":      [".ttf", ".otf", ".woff", ".woff2", ".eot"],
    "3D":         [".obj", ".fbx", ".blend", ".stl", ".dae", ".glb", ".gltf"],
}

# Reverse lookup: extension → category
EXT_TO_CATEGORY: dict[str, str] = {
    ext: cat
    for cat, exts in CATEGORY_RULES.items()
    for ext in exts
}

# Default fallback category
DEFAULT_CATEGORY: str = "Others"

# ---------------------------------------------------------------------------
# Watcher (real-time monitoring)
# ---------------------------------------------------------------------------
WATCHER_DEBOUNCE_SECONDS: float = 2.0   # coalesce rapid bursts of events

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
