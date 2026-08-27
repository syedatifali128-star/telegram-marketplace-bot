#!/usr/bin/env bash
# Simple SQLite backup — copies data/app.db into backups/ with a timestamp.
# Run manually, or on a cron schedule, e.g.:
#   0 * * * * /path/to/project/backup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$SCRIPT_DIR/data/app.db"
BACKUP_DIR="$SCRIPT_DIR/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "No database found at $DB_PATH — nothing to back up yet."
    exit 0
fi

# sqlite3 .backup is safe to run while the app is live (unlike a raw cp,
# which can copy a half-written page if a write is in progress).
if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/app_$TIMESTAMP.db'"
else
    cp "$DB_PATH" "$BACKUP_DIR/app_$TIMESTAMP.db"
fi

echo "Backup written to $BACKUP_DIR/app_$TIMESTAMP.db"

# Keep the last 30 backups only, delete older ones.
cd "$BACKUP_DIR"
ls -1t app_*.db 2>/dev/null | tail -n +31 | xargs -r rm --
