"""Daily database backup — keeps last 3 copies.

Called by automation scheduler.
Backups stored in backend/data/backups/aaa_backup_YYYYMMDD.db
"""
import shutil
import os
from datetime import datetime
from pathlib import Path

# Resolve paths relative to this script's location
BASE = Path(__file__).resolve().parent.parent  # project root
DB_PATH = BASE / "backend" / "data" / "aaa.db"
BACKUP_DIR = BASE / "backend" / "data" / "backups"
MAX_BACKUPS = 3

if not DB_PATH.exists():
    print(f"[skip] No database at {DB_PATH}")
    exit(0)

BACKUP_DIR.mkdir(parents=True, exist_ok=True)

today = datetime.now().strftime("%Y%m%d")
backup_path = BACKUP_DIR / f"aaa_backup_{today}.db"

# Skip if already backed up today
if backup_path.exists():
    print(f"[skip] Already backed up today: {backup_path}")
    exit(0)

# Copy database
shutil.copy2(str(DB_PATH), str(backup_path))
print(f"[ok] Backup created: {backup_path}")

# Prune old backups — keep MAX_BACKUPS most recent
existing = sorted(BACKUP_DIR.glob("aaa_backup_*.db"), key=os.path.getmtime, reverse=True)
for old in existing[MAX_BACKUPS:]:
    old.unlink()
    print(f"[prune] Removed old backup: {old}")

print(f"[done] {len(existing[:MAX_BACKUPS])} backups retained")
