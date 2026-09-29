#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing restore. Re-run with CONFIRM_RESTORE=YES" >&2
  exit 2
fi
BACKUP_DIR="${1:-}"
[[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]] || { echo "usage: CONFIRM_RESTORE=YES $0 /var/backups/velo/<timestamp>" >&2; exit 2; }
ENV_FILE="${VELO_BACKUP_ENV:-/etc/velo/backup.env}"
[[ -r "$ENV_FILE" ]] || { echo "missing $ENV_FILE" >&2; exit 2; }
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${VELO_BACKUP_DATABASE_URL:?missing VELO_BACKUP_DATABASE_URL}"
: "${VELO_UPLOAD_DIR:?missing VELO_UPLOAD_DIR}"

(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS)
pg_restore --dbname="$VELO_BACKUP_DATABASE_URL" --clean --if-exists --no-owner --no-acl "$BACKUP_DIR/database.dump"
mkdir -p "$VELO_UPLOAD_DIR"
rm -rf "${VELO_UPLOAD_DIR:?}"/*
tar -C "$VELO_UPLOAD_DIR" -xzf "$BACKUP_DIR/uploads.tar.gz"
echo "restore complete"
