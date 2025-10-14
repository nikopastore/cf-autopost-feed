#!/usr/bin/env python3
"""
Backup and rollback manager for RSS feeds.
Maintains rolling backups to enable recovery from bad content generation.
"""

import os
import shutil
import glob
from datetime import datetime
from typing import Optional, List
from logger_config import get_logger

logger = get_logger(__name__)

BACKUP_DIR = "backups"
DEFAULT_KEEP_COUNT = 30


def ensure_backup_dir() -> None:
    """Create backup directory if it doesn't exist."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"Created backup directory: {BACKUP_DIR}")


def backup_file(file_path: str, keep_count: int = DEFAULT_KEEP_COUNT) -> Optional[str]:
    """
    Create a timestamped backup of the specified file.

    Args:
        file_path: Path to file to backup
        keep_count: Number of recent backups to retain

    Returns:
        Path to backup file, or None if backup failed
    """
    if not os.path.exists(file_path):
        logger.warning(f"Cannot backup non-existent file: {file_path}")
        return None

    ensure_backup_dir()

    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_basename = os.path.basename(file_path)
    file_name, file_ext = os.path.splitext(file_basename)
    backup_filename = f"{file_name}_{timestamp}{file_ext}"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")

        # Cleanup old backups
        cleanup_old_backups(file_basename, keep_count)

        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup of {file_path}: {e}")
        return None


def cleanup_old_backups(file_pattern: str, keep_count: int) -> None:
    """
    Remove old backups, keeping only the most recent ones.

    Args:
        file_pattern: Base filename to match (e.g., "rss.xml")
        keep_count: Number of recent backups to retain
    """
    file_name, file_ext = os.path.splitext(file_pattern)
    pattern = os.path.join(BACKUP_DIR, f"{file_name}_*{file_ext}")
    backups = sorted(glob.glob(pattern), reverse=True)

    if len(backups) <= keep_count:
        return

    # Delete old backups
    for old_backup in backups[keep_count:]:
        try:
            os.remove(old_backup)
            logger.info(f"Deleted old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Failed to delete old backup {old_backup}: {e}")


def list_backups(file_pattern: str) -> List[str]:
    """
    List all backups for a given file pattern.

    Args:
        file_pattern: Base filename to match (e.g., "rss.xml")

    Returns:
        List of backup file paths, newest first
    """
    file_name, file_ext = os.path.splitext(file_pattern)
    pattern = os.path.join(BACKUP_DIR, f"{file_name}_*{file_ext}")
    return sorted(glob.glob(pattern), reverse=True)


def restore_backup(backup_path: str, target_path: str) -> bool:
    """
    Restore a backup file to the target location.

    Args:
        backup_path: Path to backup file
        target_path: Path where file should be restored

    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(backup_path):
        logger.error(f"Backup file not found: {backup_path}")
        return False

    try:
        # Create backup of current file before restoring
        if os.path.exists(target_path):
            backup_file(target_path, keep_count=DEFAULT_KEEP_COUNT)

        shutil.copy2(backup_path, target_path)
        logger.info(f"Restored backup {backup_path} to {target_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        return False


def get_latest_backup(file_pattern: str) -> Optional[str]:
    """
    Get the path to the most recent backup for a file.

    Args:
        file_pattern: Base filename to match (e.g., "rss.xml")

    Returns:
        Path to most recent backup, or None if no backups exist
    """
    backups = list_backups(file_pattern)
    return backups[0] if backups else None
