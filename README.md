# Family Media Catalog (Flask)

Simple Flask application for managing a family media catalog (books, audio, video).

## Prerequisites

- Python 3.11+ installed and on your `PATH`
- On Windows, install Python from [python.org](https://www.python.org/downloads/) (or the Microsoft Store) and enable **“Add python.exe to PATH”** during setup. The `python` / `python3` commands should work in a new terminal.

## Quick start

### 1. Create a virtual environment

From the project root:

**Linux / macOS**

```bash
python3 -m venv .venv
```

**Windows (PowerShell or Command Prompt)**

```powershell
python -m venv .venv
```

(`python3 -m venv .venv` also works on many Windows installs.)

If a previous attempt left a broken `.venv` folder, delete it first and run the command again.

### 2. Activate the virtual environment

Activation puts the project’s Python and `pip` on your `PATH`. The folder layout differs by OS:

| OS | Activate script |
|----|-----------------|
| Linux / macOS | `.venv/bin/activate` |
| Windows | `.venv\Scripts\activate` |

**Linux / macOS (bash/zsh)**

```bash
source .venv/bin/activate
```

**Windows — PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script (“running scripts is disabled”), either allow scripts for your user (one-time):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

or use **Command Prompt** instead:

```bat
.venv\Scripts\activate.bat
```

**Without activating** (works on any OS): call the venv’s Python directly, e.g. `.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on Linux.

Your prompt should show `(.venv)` when activation succeeded.

### 3. Install dependencies

With the venv activated:

```bash
pip install -r requirements.txt
```

Or, without activating (Windows example):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configure environment (`.env`)

Copy [`.env.example`](.env.example) to `.env` in the project root and fill in your values. That file lists every setting, with comments for local Linux vs Windows-over-SSH setups. The app loads `.env` automatically on startup (`python-dotenv`).

- Omit `DATABASE_URL` to use a local SQLite file (`db.sqlite3`) for quick testing.
- Omit optional API keys if you do not need those features (see comments in `.env.example`).

On Linux, when PostgreSQL runs on the same machine, set `DATABASE_URL` to use `localhost:5432` and leave the SSH tunnel variables unset; skip section 4b.

### 4b. Remote database from Windows (SSH tunnel)

When the database lives on a Linux server on your network, use an SSH tunnel so `DATABASE_URL` can target `localhost` on your laptop (PostgreSQL stays on the server; only SSH crosses the network). Configure `SSH_TUNNEL_*` and matching `DATABASE_URL` port values in `.env` per [`.env.example`](.env.example).

1. **Terminal 1** — start the tunnel (leave it running):

   Do **not** run `db-tunnel.ps1` from Git Bash or by double-clicking it — Windows may ask which app should “open” the file. Use one of these instead:

   **Easiest (any terminal — CMD, PowerShell, or Git Bash)**

   ```bat
   scripts\db-tunnel.bat
   ```

   **PowerShell** (must be a PowerShell window, not Git Bash)

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\db-tunnel.ps1
   ```

   **Git Bash / Linux / macOS**

   ```bash
   bash scripts/db-tunnel.sh
   ```

2. **Terminal 2** — test the connection, then run the app (see section 5).

   Requires [OpenSSH client](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) on Windows (`ssh` in your PATH).

**Tunnel fails with “cannot listen to port 5432”?** Another program (often local PostgreSQL) is using that port. Use `SSH_TUNNEL_LOCAL_PORT` and the matching port in `DATABASE_URL` as shown in [`.env.example`](.env.example), then restart the tunnel. On Windows: `netstat -ano | findstr :5432`.

### 5. Run the app

With the venv activated (or call the venv Python directly on Windows):

```bash
python scripts/test_db.py    # optional; verifies DATABASE_URL
flask run --host=127.0.0.1 --port=5000
# or
python app.py
```

Windows without activating the venv:

```powershell
.\.venv\Scripts\python.exe scripts\test_db.py
.\.venv\Scripts\python.exe -m flask run --host=127.0.0.1 --port=5000
```

### 6. Open http://127.0.0.1:5000 in your browser.

