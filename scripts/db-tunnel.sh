#!/usr/bin/env bash
# Start SSH port forward: local machine -> PostgreSQL on Linux server.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and set SSH_TUNNEL_* values." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${SSH_TUNNEL_HOST:?Set SSH_TUNNEL_HOST in .env}"
: "${SSH_TUNNEL_USER:?Set SSH_TUNNEL_USER in .env}"

LOCAL_PORT="${SSH_TUNNEL_LOCAL_PORT:-5432}"
REMOTE_HOST="${SSH_TUNNEL_REMOTE_HOST:-127.0.0.1}"
REMOTE_PORT="${SSH_TUNNEL_REMOTE_PORT:-5432}"

TARGET="${SSH_TUNNEL_USER}@${SSH_TUNNEL_HOST}"
FORWARD="${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}"

echo "SSH tunnel: localhost:${LOCAL_PORT} -> ${TARGET} (${REMOTE_HOST}:${REMOTE_PORT})"
echo "Press Ctrl+C to stop. Keep this window open while using the app."
echo

exec ssh -N -L "${FORWARD}" "${TARGET}"
