"""
OmniOS Snapshot Manager
=======================
Config-level version control. Takes snapshots of all OmniOS config files and
stores them as timestamped JSON documents in .omnios-snapshots/.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR       = Path(__file__).parent.parent
SNAPSHOTS_DIR  = BASE_DIR / ".omnios-snapshots"
MAX_SNAPSHOTS  = 50

CONFIG_FILES = [
    ".omnios-config.json",
    ".omnios-defaults.json",
    ".omnios-git-config.json",
    ".omnios-ai-config.json",
    ".omnios-connections.json",
]


def _ensure_dir() -> None:
    SNAPSHOTS_DIR.mkdir(exist_ok=True)


# ── Public API ────────────────────────────────────────────────────────────────

def create_snapshot(label: str = "") -> dict:
    """Capture all config files into a new snapshot. Returns a summary dict."""
    _ensure_dir()
    ts      = int(time.time())
    snap_id = f"snap_{ts}"

    files: dict[str, object] = {}
    for fname in CONFIG_FILES:
        fpath = BASE_DIR / fname
        if fpath.exists():
            try:
                files[fname] = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                files[fname] = None  # record that file existed but was unreadable

    snap = {
        "id":         snap_id,
        "label":      label.strip() or f"Snapshot — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ts":         ts,
        "files":      files,
    }
    (SNAPSHOTS_DIR / f"{snap_id}.json").write_text(
        json.dumps(snap, indent=2, ensure_ascii=False)
    )
    _rotate()
    _log(f"Snapshot created: {snap['label']}")
    return {
        "id":         snap_id,
        "label":      snap["label"],
        "created_at": snap["created_at"],
        "file_count": len([v for v in files.values() if v is not None]),
    }


def list_snapshots() -> list[dict]:
    """Return all snapshots as summaries, newest first."""
    _ensure_dir()
    snaps = []
    for f in sorted(SNAPSHOTS_DIR.glob("snap_*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            snaps.append({
                "id":         data["id"],
                "label":      data.get("label", data["id"]),
                "created_at": data.get("created_at", ""),
                "ts":         data.get("ts", 0),
                "file_count": len([v for v in data.get("files", {}).values() if v is not None]),
            })
        except Exception:
            pass
    return snaps


def restore_snapshot(snap_id: str) -> dict:
    """
    Restore config files from a snapshot.
    Creates a safety backup automatically before overwriting anything.
    """
    snap_path = SNAPSHOTS_DIR / f"{snap_id}.json"
    if not snap_path.exists():
        return {"ok": False, "error": "Snapshot not found"}
    try:
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"Could not read snapshot: {exc}"}

    # Safety net — capture current state before any overwrites
    create_snapshot("Pre-restore backup (auto)")

    restored: list[str] = []
    for fname, content in snap.get("files", {}).items():
        if content is None:
            continue
        fpath = BASE_DIR / fname
        try:
            fpath.write_text(json.dumps(content, indent=2, ensure_ascii=False))
            restored.append(fname)
        except Exception:
            pass

    # Push changes into the live app
    try:
        from . import config_manager as _cm
        _cm._reload_into_app()
    except Exception:
        pass

    _log(f"Config restored from: {snap.get('label', snap_id)}")
    return {"ok": True, "restored": restored, "label": snap.get("label", snap_id)}


def delete_snapshot(snap_id: str) -> dict:
    snap_path = SNAPSHOTS_DIR / f"{snap_id}.json"
    if not snap_path.exists():
        return {"ok": False, "error": "Snapshot not found"}
    snap_path.unlink()
    return {"ok": True}


def get_snapshot(snap_id: str) -> dict | None:
    snap_path = SNAPSHOTS_DIR / f"{snap_id}.json"
    if not snap_path.exists():
        return None
    try:
        return json.loads(snap_path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rotate() -> None:
    files = sorted(SNAPSHOTS_DIR.glob("snap_*.json"), reverse=True)
    for old in files[MAX_SNAPSHOTS:]:
        try:
            old.unlink()
        except Exception:
            pass


def _log(msg: str) -> None:
    try:
        from .log_manager import write_log
        write_log("system", "info", msg)
    except Exception:
        pass
