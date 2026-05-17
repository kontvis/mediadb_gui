"""Verify DATABASE_URL can connect (run while SSH tunnel is up)."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL is not set (check your .env file).", file=sys.stderr)
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print(
        "Install dependencies: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    conn = psycopg2.connect(url)
    conn.close()
except Exception as exc:
    print(f"Connection failed: {exc}", file=sys.stderr)
    print(
        "Is the SSH tunnel running?  .\\scripts\\db-tunnel.ps1",
        file=sys.stderr,
    )
    sys.exit(1)

print("Database connection OK.")
