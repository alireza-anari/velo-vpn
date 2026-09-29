#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${VELO_BACKUP_ENV:-/etc/velo/backup.env}"
[[ -r "$ENV_FILE" ]] || { echo "missing $ENV_FILE" >&2; exit 2; }
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${VELO_BACKUP_DATABASE_URL:?missing VELO_BACKUP_DATABASE_URL}"
: "${VELO_UPLOAD_DIR:?missing VELO_UPLOAD_DIR}"
: "${VELO_BACKUP_DIR:?missing VELO_BACKUP_DIR}"
RETENTION="${VELO_BACKUP_RETENTION_DAYS:-14}"

umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="${VELO_BACKUP_DIR}/.${stamp}.tmp"
out="${VELO_BACKUP_DIR}/${stamp}"
mkdir -p "$tmp"

cleanup(){ rm -rf "$tmp"; }
trap cleanup EXIT

pg_dump --dbname="$VELO_BACKUP_DATABASE_URL" --format=custom --no-owner --no-acl --file="$tmp/database.dump"
if [[ -d "$VELO_UPLOAD_DIR" ]]; then
  tar -C "$VELO_UPLOAD_DIR" -czf "$tmp/uploads.tar.gz" .
else
  tar -czf "$tmp/uploads.tar.gz" --files-from /dev/null
fi
(
  cd "$tmp"
  sha256sum database.dump uploads.tar.gz > SHA256SUMS
  printf 'created_at_utc=%s\n' "$stamp" > MANIFEST
)
mv "$tmp" "$out"
trap - EXIT

find "$VELO_BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -mtime "+$RETENTION" -exec rm -rf {} +
echo "$out"
