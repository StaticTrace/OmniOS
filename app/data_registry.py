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
    """Collect every localStorage key across all modules."""
    keys: list[str] = []
    for m in _MODULES:
        keys.extend(m["client_keys"])
    return list(dict.fromkeys(keys))  # deduplicate, preserve order


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

# Home — no persistent storage yet; registered for future use
register_module(
    id="home",
    label="Home",
    description="Cached UI state and any saved home page preferences",
    client_keys=["omnios-home-prefs"],
)

# Dashboard
register_module(
    id="dashboard",
    label="Dashboard",
    description="Quick-links list, daily focus note, and widget preferences",
    client_keys=["omnios-quick-links", "omnios-focus"],
)

# Social Hub — no persisted client state currently; registered for future use
register_module(
    id="social",
    label="Social Hub",
    description="Cached social feed state and display preferences",
    client_keys=["omnios-social-prefs"],
)

# Notifications
register_module(
    id="notifications",
    label="Notifications",
    description="Saved RSS/notification sources and feed preferences",
    client_keys=["omnios-rss-sources"],
)

# Email Aliases
register_module(
    id="email-alias",
    label="Email Aliases",
    description="All generated email aliases and their labels",
    client_keys=["omnios-aliases"],
)

# Portfolio
register_module(
    id="portfolio",
    label="Portfolio",
    description="Saved projects, descriptions, tags, and links",
    client_keys=["omnios-projects"],
)

# Contact
register_module(
    id="contact",
    label="Contact",
    description="Saved contact form message history",
    client_keys=["omnios-contact-msgs"],
)

# Git / GitHub integration (server-side)
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

# Secrets / .env (server-side)
def _clean_env_secrets() -> list[str]:
    done = []
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        env_file.unlink()
        done.append("Deleted .env (GITHUB_PAT and other secrets)")
    for key in ("GITHUB_PAT",):
        if key in os.environ:
            del os.environ[key]
            done.append(f"Cleared {key} from process environment")
    return done

register_module(
    id="env-secrets",
    label="Stored Secrets",
    description="GitHub PAT and any other saved environment secrets",
    client_keys=[],
    server_cleaner=_clean_env_secrets,
)

# Generic catch-all for future *.omnios-data.json files
def _clean_data_files() -> list[str]:
    done = []
    for f in BASE_DIR.glob("*.omnios-data.json"):
        f.unlink()
        done.append(f"Deleted {f.name}")
    return done

register_module(
    id="user-data-files",
    label="Data Files",
    description="Any additional module data files stored on disk",
    client_keys=[],
    server_cleaner=_clean_data_files,
)
