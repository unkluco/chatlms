from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

HEALTH_PATH = Path(__file__).resolve().parent / "bot_health.json"


def write_health(status="running", **extra):
    data = {
        "status": status,
        "pid": os.getpid(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        **extra,
    }
    try:
        HEALTH_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def cleanup_old_attachments(folder, max_age_hours=24):
    try:
        root = Path(folder)
        if not root.exists():
            return 0
        now = time.time()
        removed = 0
        for item in root.rglob("*"):
            try:
                if item.is_file() and now - item.stat().st_mtime > max_age_hours * 3600:
                    item.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                continue
        return removed
    except Exception:
        return 0


def get_process_memory_mb(pid=None):
    try:
        import psutil
        process = psutil.Process(pid or os.getpid())
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except Exception:
        return None


def get_children_memory_mb(pid):
    """Tong RAM process con (dung cho Playwright/Chrome watchdog)."""
    try:
        import psutil
        root = psutil.Process(pid)
        total = 0
        for child in root.children(recursive=True):
            try:
                total += child.memory_info().rss
            except Exception:
                continue
        return round(total / 1024 / 1024, 2)
    except Exception:
        return None


def should_restart_browser(max_python_mb=800):
    memory = get_process_memory_mb()
    return memory is not None and memory > max_python_mb


def should_restart_browser_tree(browser_pid, max_children_mb=1500):
    memory = get_children_memory_mb(browser_pid)
    return memory is not None and memory > max_children_mb


def find_browser_memory_mb(parent_pid):
    """Tong RAM process con cua bot (bao gom Playwright/Chrome neu la child)."""
    return get_children_memory_mb(parent_pid)
