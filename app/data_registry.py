"""
OmniOS Data Registry
====================
Central registry for user data. Each module registers its own entry so the
"Clean All Personal Data" wipe knows exactly what to delete — both server-side
files and client-side localStorage keys.

Usage (in any module):
    from .data_registry import register_module

    register_module(
        id="my-feature",
        label="My Feature",
        description="Saved settings and preferences for My Feature",
        client_keys=["omnios-my-key"],        # localStorage keys to clear
        server_cleaner=lambda: ["Deleted X"], # optional backend cleanup fn
    )
"""

import os
import shutil
from pathlib import Path
from typing import Callable

BASE_DIR = Path(__file__).parent.parent

# ── Registry store ────────────────────────────────────────────────────────────

_MODULES: list[dict] = []


def register_module(
    id: str,
    label: str,
    description: str,
    client_keys: list[str] | None = None,
    server_cleaner: Callable[[], list[str]] | None = None,
) -> None:
    """Register a module's data with the wipe registry."""
    _MODULES.append({
        "id": id,
        "label": label,
        "description": description,
        "client_keys": client_keys or [],
        "server_cleaner": server_cleaner,
    })


def get_manifest() -> list[dict]:
    """Return a public manifest (no callables) describing all registered data."""
    return [
        {
            "id": m["id"],
            "label": m["label"],
            "description": m["description"],
            "client_keys": m["client_keys"],
            "has_server_data": m["server_cleaner"] is not None,
        }
        for m in _MODULES
    ]


def get_all_client_keys() -> list[str]:
    """Collect every localStorage key across all modules (deduplicated)."""
    keys: list[str] = []
    for m in _MODULES:
        keys.extend(m["client_keys"])
    return list(dict.fromkeys(keys))


def run_all_cleaners() -> dict:
    """Run every server-side cleaner and return a summary report."""
    log: list[str] = []
    errors: list[str] = []
    for m in _MODULES:
        fn = m.get("server_cleaner")
        if fn is None:
            continue
        try:
            results = fn() or []
            for r in results:
                log.append(f"[{m['id']}] {r}")
        except Exception as exc:
            errors.append(f"[{m['id']}] ERROR: {exc}")
    return {
        "log": log,
        "errors": errors,
        "ok": len(errors) == 0,
        "client_keys": get_all_client_keys(),
    }


# ── Module registrations ──────────────────────────────────────────────────────

register_module(
    id="home",
    label="Home",
    description="Cached UI state and any saved home page preferences",
    client_keys=["omnios-home-prefs"],
)

register_module(
    id="dashboard",
    label="Dashboard",
    description="Quick-links list, daily focus note, and widget preferences",
    client_keys=["omnios-quick-links", "omnios-focus"],
)

register_module(
    id="social",
    label="Social Hub",
    description="Cached social feed state and display preferences",
    client_keys=["omnios-social-prefs"],
)

register_module(
    id="notifications",
    label="Notifications",
    description="Saved RSS/notification sources and feed preferences",
    client_keys=["omnios-rss-sources"],
)

register_module(
    id="email-alias",
    label="Email Aliases",
    description="All generated email aliases and their labels",
    client_keys=["omnios-aliases"],
)

register_module(
    id="portfolio",
    label="Portfolio",
    description="Saved projects, descriptions, tags, and links",
    client_keys=["omnios-projects"],
)

register_module(
    id="contact",
    label="Contact",
    description="Saved contact form message history",
    client_keys=["omnios-contact-msgs"],
)

# ── AI Assistant ──────────────────────────────────────────────────────────────

def _clean_ai_data() -> list[str]:
    done = []
    cfg_file = BASE_DIR / ".omnios-ai-config.json"
    if cfg_file.exists():
        cfg_file.unlink()
        done.append("Deleted .omnios-ai-config.json (AI provider and model preferences)")
    return done

register_module(
    id="ai-assistant",
    label="AI Assistant",
    description="Saved AI provider, model, and system prompt preferences; chat history",
    client_keys=["omnios-ai-history"],
    server_cleaner=_clean_ai_data,
)

# ── System Logs ───────────────────────────────────────────────────────────────

def _clean_logs() -> list[str]:
    done = []
    log_file = BASE_DIR / ".omnios-logs.jsonl"
    if log_file.exists():
        log_file.unlink()
        done.append("Deleted .omnios-logs.jsonl (all system log entries)")
    return done

register_module(
    id="system-logs",
    label="System Logs",
    description="Structured activity log recorded by all OmniOS modules",
    client_keys=[],
    server_cleaner=_clean_logs,
)

# ── Snapshots ─────────────────────────────────────────────────────────────────

def _clean_snapshots() -> list[str]:
    done = []
    snap_dir = BASE_DIR / ".omnios-snapshots"
    if snap_dir.exists():
        count = len(list(snap_dir.glob("*.json")))
        shutil.rmtree(snap_dir)
        done.append(f"Deleted .omnios-snapshots/ ({count} snapshot(s) removed)")
    return done

register_module(
    id="snapshots",
    label="Config Snapshots",
    description="Saved configuration snapshots created via the Snapshots page",
    client_keys=[],
    server_cleaner=_clean_snapshots,
)

# ── Git / GitHub integration ──────────────────────────────────────────────────

def _clean_git_config() -> list[str]:
    done = []
    cfg_file = BASE_DIR / ".omnios-git-config.json"
    if cfg_file.exists():
        cfg_file.unlink()
        done.append("Deleted .omnios-git-config.json")
    return done

register_module(
    id="git-config",
    label="GitHub Integration",
    description="Saved repository URL, git username, and email",
    client_keys=[],
    server_cleaner=_clean_git_config,
)

# ── Stored Secrets (.env) ─────────────────────────────────────────────────────

# All keys managed by the Connections page and the Git integration.
_ALL_SECRET_KEYS = (
    "GITHUB_PAT",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_AI_KEY",
    "YOUTUBE_API_KEY",
    "CUSTOM_AI_KEY",
)

def _clean_env_secrets() -> list[str]:
    done = []
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        env_file.unlink()
        done.append("Deleted .env (all stored secrets)")
    for key in _ALL_SECRET_KEYS:
        if key in os.environ:
            del os.environ[key]
            done.append(f"Cleared {key} from process environment")
    return done

register_module(
    id="env-secrets",
    label="Stored Secrets",
    description="All API keys and secrets saved via the Connections page",
    client_keys=[],
    server_cleaner=_clean_env_secrets,
)

# ── Connections metadata ──────────────────────────────────────────────────────

def _clean_connections_meta() -> list[str]:
    done = []
    cfg_file = BASE_DIR / ".omnios-connections.json"
    if cfg_file.exists():
        cfg_file.unlink()
        done.append("Deleted .omnios-connections.json (connection metadata)")
    return done

register_module(
    id="connections",
    label="Connections",
    description="Saved connection metadata for all configured API integrations",
    client_keys=[],
    server_cleaner=_clean_connections_meta,
)

# ── Config overrides ──────────────────────────────────────────────────────────

def _clean_config_overrides() -> list[str]:
    done = []
    cfg_file = BASE_DIR / ".omnios-config.json"
    if cfg_file.exists():
        cfg_file.unlink()
        done.append("Deleted .omnios-config.json (active config overrides)")
    return done

register_module(
    id="config-overrides",
    label="Config Overrides",
    description="Active configuration edits made in the Config Editor",
    client_keys=[],
    server_cleaner=_clean_config_overrides,
)

# ── Saved default config ──────────────────────────────────────────────────────

def _clean_config_defaults() -> list[str]:
    done = []
    defaults_file = BASE_DIR / ".omnios-defaults.json"
    if defaults_file.exists():
        defaults_file.unlink()
        done.append("Deleted .omnios-defaults.json (user-saved default config)")
    try:
        from .config_manager import _reload_into_app
        _reload_into_app()
    except Exception:
        pass
    return done

register_module(
    id="config-defaults",
    label="Saved Default Config",
    description="Your custom default configuration saved via 'Save As Default'",
    client_keys=[],
    server_cleaner=_clean_config_defaults,
)

# ── Catch-all for legacy *.omnios-data.json files ─────────────────────────────

def _clean_data_files() -> list[str]:
    done = []
    for f in BASE_DIR.glob("*.omnios-data.json"):
        f.unlink()
        done.append(f"Deleted {f.name}")
    return done

register_module(
    id="user-data-files",
    label="Legacy Data Files",
    description="Any additional module data files stored on disk",
    client_keys=[],
    server_cleaner=_clean_data_files,
)
