"""Automated SQLite Live Backup Script for AirPurify AI.

Uses Python's native sqlite3 online backup API to take a non-blocking,
consistent snapshot of the active database while the FastAPI server is running.
"""
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sqlite3
import sys

logger = logging.getLogger("airpurify.backup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BACKEND_DIR / "airpurify.db"
DEFAULT_BACKUP_DIR = BACKEND_DIR / "backups"


def perform_backup(
    db_path: Path = DEFAULT_DB_PATH,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    max_retentions: int = 7,
) -> Path:
    """Create a consistent snapshot of the active SQLite database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found at: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"airpurify_backup_{timestamp_str}.db"

    logger.info("Starting live online backup: %s -> %s", db_path, backup_file)
    src_con = sqlite3.connect(str(db_path))
    dst_con = sqlite3.connect(str(backup_file))

    try:
        # Non-blocking page-by-page atomic backup
        with dst_con:
            src_con.backup(dst_con, pages=50, sleep=0.01)
        logger.info("Backup complete (%d bytes written).", backup_file.stat().st_size)
    finally:
        dst_con.close()
        src_con.close()

    # Enforce retention policy: prune older backups
    existing_backups = sorted(backup_dir.glob("airpurify_backup_*.db"))
    if len(existing_backups) > max_retentions:
        prune_count = len(existing_backups) - max_retentions
        for old_file in existing_backups[:prune_count]:
            logger.info("Pruning old backup per retention policy: %s", old_file.name)
            old_file.unlink()

    return backup_file


if __name__ == "__main__":
    try:
        out = perform_backup()
        print(f"SUCCESS: Backup created at {out}")
    except Exception as e:
        logger.error("Database backup failed: %s", e)
        sys.exit(1)
