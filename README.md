# Smart File Organizer AI

> A production-grade, cross-platform desktop application that autonomously scans, classifies, and organizes your entire file system — powered by a Python + Rust engine, FastAPI backend, and Electron + React frontend.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 **Smart Scanning** | Multi-threaded `os.scandir()` scanner — 3–5× faster than `os.walk()` |
| 🧠 **AI-Ready Classifier** | Rule-based (extension · glob · regex) with confidence scores, AI hook-ready |
| 📁 **Safe Organizer** | Same-drive atomic rename · cross-drive buffered copy · full undo support |
| 🔁 **Duplicate Detector** | 3-stage: size → partial hash → XXHash64 |
| 👁️ **Dry-Run Mode** | Preview every operation before committing |
| 📡 **Real-Time Progress** | WebSocket progress pushed to UI |
| 👀 **Filesystem Watcher** | Watchdog-based live monitoring · debounced events |
| 📊 **Rich Dashboard** | Category pie chart · file stats · one-click organize |
| 🛡️ **Safety Guard** | Protected system paths hardcoded; never modified |
| ↩️ **Full Undo** | Every move logged; one-click revert |
| ⚡ **Rust Engine** | PyO3 FFI bridge for scanner + hasher (Phase 6) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           Electron Desktop App               │
│  Dashboard · Preview · Rules · Logs · Config │
│      React 18 + Tailwind CSS + Zustand       │
└──────────────────┬──────────────────────────┘
                   │ HTTP REST + WebSocket
┌──────────────────▼──────────────────────────┐
│          FastAPI Backend (port 8765)         │
│  /api/scan  /api/organize  /api/rules  /ws  │
└──────┬─────────────┬───────────────┬────────┘
       │             │               │
   Scanner       Organizer      Watcher
  (threads +     (mover +       (Watchdog
   Rust FFI)      logger)        events)
       │
┌──────▼──────────────────────────────────────┐
│       SQLite  (→ PostgreSQL upgrade path)    │
│  files · logs · rules · undo_history         │
└─────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
smart-file-organizer/
├── backend/                  # Python FastAPI backend
│   ├── main.py               # App entry point + lifespan
│   ├── config.py             # All constants + classification rules
│   ├── database/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── connection.py     # Async engine + session factory
│   ├── core/
│   │   ├── scanner.py        # Multi-threaded os.scandir() scanner
│   │   ├── classifier.py     # Rule-based file classifier
│   │   ├── mover.py          # Safe file mover + undo manager
│   │   ├── duplicate_detector.py  # 3-stage dedup engine
│   │   └── watcher.py        # Watchdog wrapper
│   ├── api/
│   │   ├── routes/           # scan · organize · rules · logs
│   │   └── websocket.py      # Real-time progress
│   ├── services/             # Business logic orchestrators
│   ├── schemas/schemas.py    # Pydantic v2 request/response types
│   └── requirements.txt
│
├── rust_engine/              # Rust performance module (Phase 6)
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs            # PyO3 FFI entry point
│       ├── scanner.rs        # walkdir + rayon parallel scan
│       └── hasher.rs         # XXHash64 parallel hasher
│
├── frontend/                 # Electron + React UI
│   ├── electron/
│   │   ├── main.js           # Main process + backend launcher
│   │   └── preload.js        # Secure IPC bridge
│   └── src/
│       ├── components/       # Dashboard · Preview · Rules · Logs · Settings
│       ├── store/appStore.ts # Zustand global state
│       ├── hooks/            # useWebSocket
│       ├── lib/api.ts        # Typed Axios API client
│       └── index.css         # Design tokens + utilities
│
├── tests/                    # pytest test suite
│   ├── test_classifier.py
│   ├── test_scanner.py
│   ├── test_mover.py
│   ├── test_duplicate_detector.py
│   └── test_api.py           # FastAPI integration tests
│
├── scripts/
│   ├── build.ps1             # Full Windows build pipeline
│   └── dev.ps1               # Dev mode launcher
│
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Minimum Version |
|---|---|
| Python | 3.11+ |
| Node.js | 20+ |
| Rust | 1.75+ (via [rustup](https://rustup.rs)) |

### 1 — Clone & set up Python backend

```powershell
cd E:\Project\smart-file-organizer

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt
```

### 2 — Start the backend

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

API docs live at: **http://localhost:8765/api/docs**

### 3 — Start the frontend

```powershell
cd frontend
npm install
npm run dev:vite        # Just the React UI in browser (quick preview)
# OR
npm run dev             # Full Electron app
```

### 4 — One-command dev mode

```powershell
.\scripts\dev.ps1
```

---

## 🧪 Running Tests

```powershell
# Unit + integration tests
python -m pytest tests\ -v

# Skip slow tests
python -m pytest tests\ -v -m "not slow"

# With coverage
pip install pytest-cov
python -m pytest tests\ --cov=backend --cov-report=html
```

---

## ⚡ Building Rust Engine (Phase 6)

```powershell
cd rust_engine

# Install Maturin (PyO3 build tool)
pip install maturin

# Build + install into current venv
maturin develop --release

# Test
cargo test --release
```

After building, the engine is importable in Python:

```python
import smart_organizer_engine as engine

files = engine.scan_directory("C:\\Users\\You\\Downloads")
hashes = engine.hash_files([f["path"] for f in files])
```

---

## 📦 Production Build

```powershell
# Full build: Rust + PyInstaller + Electron NSIS installer
.\scripts\build.ps1

# Backend only
.\scripts\build.ps1 -Backend

# Frontend only
.\scripts\build.ps1 -Frontend

# Skip tests (faster CI)
.\scripts\build.ps1 -SkipTests
```

Output:
- `dist\smart_organizer_backend.exe` — standalone backend
- `frontend\dist-electron\Smart File Organizer AI Setup.exe` — Windows installer

---

## 🔌 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness probe |
| `POST` | `/api/scan/start` | Start a background scan |
| `GET` | `/api/scan/sessions` | List all scan sessions |
| `GET` | `/api/scan/sessions/{id}/files` | Files from a session |
| `POST` | `/api/organize/` | Organize files (or dry-run) |
| `POST` | `/api/organize/undo` | Reverse file moves |
| `GET` | `/api/rules/` | List classification rules |
| `POST` | `/api/rules/` | Create a custom rule |
| `PUT` | `/api/rules/{id}` | Update a rule |
| `DELETE` | `/api/rules/{id}` | Delete a rule |
| `GET` | `/api/logs/` | Activity log |
| `WS` | `/api/scan/ws/progress` | Real-time progress stream |

---

## 🗄️ Database Schema

```sql
files          (id, path, name, extension, size, category, last_modified, hash, scan_session_id)
scan_sessions  (id, root_path, started_at, completed_at, total_files, status)
logs           (id, old_path, new_path, operation, status, timestamp, error_message)
undo_history   (id, log_id, original_path, can_undo, undone_at)
rules          (id, name, pattern, match_type, category, target_folder, priority, enabled)
```

**PostgreSQL migration**: Set environment variable:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/smart_organizer"
python -m uvicorn backend.main:app ...
```

All ORM models are PostgreSQL-compatible from day one.

---

## 🛡️ Safety Model

1. **Protected directories** — `C:\Windows`, `C:\Program Files`, etc. are hardcoded rejects
2. **Dry-run mode** — toggle in Settings; preview JSON returned, zero FS changes
3. **Full undo** — every move creates a `logs` + `undo_history` row; reversible anytime
4. **Atomic moves** — same-drive: `os.rename()` (atomic); cross-drive: copy → verify → delete
5. **Collision safety** — `file.pdf` → `file_(1).pdf` → `file_(2).pdf` (up to 999)

---

## 📈 Scaling to Millions of Files

| Technique | Benefit |
|---|---|
| `os.scandir()` over `os.walk()` | 3-5× fewer syscalls |
| Bounded `queue.Queue(maxsize=10_000)` | Constant RAM regardless of tree depth |
| Incremental scanning (mtime + size cache) | Skip ~95% of files on rescan |
| SQLite `INSERT OR REPLACE` in batches of 500 | Avoids per-row commit overhead |
| Rust `rayon` parallel walker | Linear CPU scaling across cores |
| XXHash64 for dedup | 10× faster than MD5, 3× faster than SHA-256 |
| Partial-hash pre-filter (64 KB) | Eliminates 90%+ of full-hash candidates |

---

## 🗺️ Roadmap

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Core engine: scanner · classifier · mover |
| 2 | ✅ Done | Database + undo logging |
| 3 | ✅ Done | FastAPI REST + WebSocket API |
| 4 | ✅ Done | Electron + React UI |
| 5 | ✅ Done | Background file watcher |
| 6 | ✅ Done | Rust FFI engine (skeleton) |
| 7 | 🔜 Next | Windows NSIS installer + auto-updater |
| 8 | 🔜 Future | NLP-based smart file naming (AI model integration) |
| 9 | 🔜 Future | Cloud sync + multi-machine support |

---

## 📄 License

MIT © Smart File Organizer AI
