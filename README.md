# Family Media Catalog (Flask)

Simple Flask application for managing a family media catalog (books, audio, video).

Quick start

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure the database (PostgreSQL) and secret key (optional):

```bash
export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'
export SECRET_KEY='your-secret'
```

If you omit `DATABASE_URL`, the app will use a local SQLite file `db.sqlite3` for easy testing.

4. Run the app:

```bash
flask run --host=127.0.0.1 --port=5000
# or
python app.py
```

5. Open http://127.0.0.1:5000 in your browser.

Pushing to GitHub

- Initialize a repo and push as usual:

```bash
git init
git add .
git commit -m "Initial media catalog app"
git remote add origin git@github.com:youruser/yourrepo.git
git push -u origin main
```
