from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEALTH = ROOT / "bot_health.json"

STALE_SECONDS = 1800
CHECK_INTERVAL = 60


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def health_ok():
    if not HEALTH.exists():
        return False
    try:
        data = json.loads(HEALTH.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(data.get("updated_at"))
        return (datetime.now() - updated).total_seconds() < STALE_SECONDS
    except Exception:
        return False


def main():
    log("LMS bot watchdog started")
    while True:
        if health_ok():
            time.sleep(CHECK_INTERVAL)
            continue

        log("Health stale or missing. Bot may need manual restart.")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
