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

### 4. Configure the database, secret key, and Google Vision API key (optional)

Copy or create a `.env` file in the project root (see your local `.env`; it is gitignored). The app reads **environment variables**, not the file itself, unless you export them or load them another way.

**Linux / macOS**

```bash
export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'
export SECRET_KEY='your-secret'
export GOOGLE_VISION_API_KEY='your-google-vision-api-key'
```

**Windows (PowerShell)**

```powershell
$env:DATABASE_URL = 'postgresql://user:pass@localhost:5432/dbname'
$env:SECRET_KEY = 'your-secret'
$env:GOOGLE_VISION_API_KEY = 'your-google-vision-api-key'
```

If you omit `DATABASE_URL`, the app will use a local SQLite file `db.sqlite3` for easy testing.
If you omit `GOOGLE_VISION_API_KEY`, photo processing will not work.

### 5. Run the app

With the venv activated:

```bash
flask run --host=127.0.0.1 --port=5000
# or
python app.py
```

### 6. Open http://127.0.0.1:5000 in your browser.

## Pushing to GitHub

- Initialize a repo and push as usual:

```bash
git init
git add .
git commit -m "Initial media catalog app"
git remote add origin git@github.com:youruser/yourrepo.git
git push -u origin main
```

Do not commit `.venv/` or `.env`; both are listed in `.gitignore`.
