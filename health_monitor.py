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


def should_restart_browser(max_python_mb=800):
    memory = get_process_memory_mb()
    return memory is not None and memory > max_python_mb
