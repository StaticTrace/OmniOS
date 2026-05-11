"""
OmniOS Log Manager
==================
Structured file-based logging. Each entry is a JSON object on its own line
(.omnios-logs.jsonl). The viewer page queries this via the /api/logs endpoint.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR  = Path(__file__).parent.parent
LOG_FILE  = BASE_DIR / ".omnios-logs.jsonl"
MAX_LINES = 2000     # rotate when file exceeds this many entries
MAX_BYTES = 2_000_000  # hard cap ~2 MB

VALID_LEVELS      = {"info", "success", "warning", "error", "debug"}
VALID_CATEGORIES  = {"system", "ai", "config", "git", "connections", "export", "user", "error"}


def write_log(category: str, level: str, message: str, data: dict | None = None) -> None:
    """Append one log entry. Never raises — logging must not break the app."""
    try:
        entry: dict = {
            "ts":       time.time(),
            "time":     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "level":    level    if level    in VALID_LEVELS     else "info",
            "category": category if category in VALID_CATEGORIES else "system",
            "message":  str(message)[:500],
        }
        if data:
            entry["data"] = data

        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

        _maybe_rotate()
    except Exception:
        pass


def get_logs(
    category: str | None = None,
    level:    str | None = None,
    limit:    int        = 300,
    search:   str | None = None,
) -> list[dict]:
    """Return filtered log entries, newest first."""
    if not LOG_FILE.exists():
        return []
    try:
        lines   = LOG_FILE.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

        if category and category != "all":
            entries = [e for e in entries if e.get("category") == category]
        if level and level != "all":
            entries = [e for e in entries if e.get("level") == level]
        if search:
            s = search.lower()
            entries = [e for e in entries if s in e.get("message", "").lower()]

        return list(reversed(entries))[:limit]
    except Exception:
        return []


def get_stats() -> dict:
    """Return aggregate counts for the log viewer dashboard."""
    if not LOG_FILE.exists():
        return {"total": 0, "by_level": {}, "by_category": {}}
    try:
        by_level:    dict[str, int] = {}
        by_category: dict[str, int] = {}
        count = 0
        for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            count += 1
            try:
                e   = json.loads(line)
                lv  = e.get("level",    "info")
                cat = e.get("category", "system")
                by_level[lv]      = by_level.get(lv, 0) + 1
                by_category[cat]  = by_category.get(cat, 0) + 1
            except Exception:
                pass
        return {"total": count, "by_level": by_level, "by_category": by_category}
    except Exception:
        return {"total": 0, "by_level": {}, "by_category": {}}


def clear_logs() -> None:
    """Delete the log file and write a single housekeeping entry."""
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
    except Exception:
        pass
    write_log("system", "info", "Logs cleared by user")


# ── Internal rotation ─────────────────────────────────────────────────────────

def _maybe_rotate() -> None:
    try:
        if LOG_FILE.stat().st_size < MAX_BYTES:
            return
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LINES:
            LOG_FILE.write_text(
                "\n".join(lines[-MAX_LINES:]) + "\n",
                encoding="utf-8",
            )
    except Exception:
        pass
