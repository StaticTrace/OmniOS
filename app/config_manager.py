"""
OmniOS Config Manager
=====================
Central configuration registry with schema-driven load / save / reset.

• Core sections are registered here.
• External modules call register_section() to add their own fields.
• Changes are persisted to .omnios-config.json (overlay on top of
  in-code defaults) and reloaded into the running process immediately.
"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE_DIR    = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / ".omnios-config.json"

# ── Registered section list (core + module-registered) ───────────────────────

_SECTIONS: list[dict] = []


def register_section(
    id: str,
    label: str,
    description: str,
    icon: str,
    fields: list[dict],
    defaults: dict | None = None,
) -> None:
    """
    Register a config section.

    Each field dict:
      key          – str   unique key within the section
      label        – str   display label
      type         – str   text | textarea | url | email | toggle | number | select
      default      – Any   value used when no override exists
      description  – str   helper text shown below the field (optional)
      options      – list  required for type=="select", list of {value, label}
      placeholder  – str   input placeholder (optional)
    """
    _SECTIONS.append({
        "id":          id,
        "label":       label,
        "description": description,
        "icon":        icon,
        "fields":      fields,
        "defaults":    defaults or {f["key"]: f["default"] for f in fields},
    })


# ── Core section registrations ────────────────────────────────────────────────

register_section(
    id="identity",
    label="Identity",
    description="Your profile shown across every page of OmniOS.",
    icon="user",
    fields=[
        {
            "key": "name", "label": "Display Name", "type": "text",
            "default": "OmniOS Hub",
            "placeholder": "OmniOS Hub",
            "description": "Shown in the sidebar and page headers.",
        },
        {
            "key": "tagline", "label": "Tagline", "type": "text",
            "default": "Your personal OS for the web",
            "placeholder": "Your personal OS for the web",
            "description": "One-line description shown on your home card.",
        },
        {
            "key": "bio", "label": "Bio", "type": "textarea",
            "default": (
                "A private, modular digital operating system built around you "
                "— unified profile, dashboard, social hub, notifications, and "
                "extensible modules so you can add or remove features as your "
                "needs evolve. Clean, minimal UI and a developer-friendly "
                "architecture for fast customization."
            ),
            "placeholder": "Write a short bio…",
            "description": "Displayed on the home page profile card.",
        },
        {
            "key": "avatar", "label": "Avatar URL", "type": "url",
            "default": "",
            "placeholder": "https://example.com/avatar.png",
            "description": "Link to a profile image. Leave blank for the default monogram.",
        },
    ],
)

register_section(
    id="social_links",
    label="Social Links",
    description="Platforms shown on your Home card and Social Hub page.",
    icon="share-2",
    fields=[],      # social links are handled as a dynamic list (special type)
    defaults={"links": [
        {"platform": "GitHub",  "url": "https://github.com/StaticTrace",                        "icon": "github"},
        {"platform": "YouTube", "url": "https://www.youtube.com/@wtfugdelittlepony7720",         "icon": "youtube"},
    ]},
)

register_section(
    id="notifications",
    label="Notification Sources",
    description="Toggle which sources feed into your Notifications page.",
    icon="bell",
    fields=[
        {
            "key": "github_enabled",  "label": "GitHub",
            "type": "toggle", "default": True,
            "description": "Pull public GitHub activity events.",
        },
        {
            "key": "youtube_enabled", "label": "YouTube",
            "type": "toggle", "default": True,
            "description": "Show YouTube channel updates (requires channel ID).",
        },
        {
            "key": "rss_enabled",     "label": "RSS Feed",
            "type": "toggle", "default": False,
            "description": "Aggregate posts from custom RSS/Atom feeds.",
        },
    ],
)

register_section(
    id="ui",
    label="UI Preferences",
    description="Appearance and behaviour settings for the hub.",
    icon="sliders",
    fields=[
        {
            "key": "github_username", "label": "GitHub Username",
            "type": "text", "default": "StaticTrace",
            "placeholder": "StaticTrace",
            "description": "Used by the GitHub Activity and Stats widgets on the Dashboard.",
        },
        {
            "key": "weather_lat", "label": "Weather Latitude",
            "type": "number", "default": "51.5074",
            "placeholder": "51.5074",
            "description": "Decimal latitude for the Weather widget (e.g. 51.5074 = London).",
        },
        {
            "key": "weather_lon", "label": "Weather Longitude",
            "type": "number", "default": "-0.1278",
            "placeholder": "-0.1278",
            "description": "Decimal longitude for the Weather widget.",
        },
        {
            "key": "sidebar_label", "label": "Sidebar Sub-label",
            "type": "text", "default": "Personal OS",
            "placeholder": "Personal OS",
            "description": "Small label shown under your name in the sidebar footer.",
        },
    ],
)

register_section(
    id="pages",
    label="Page Visibility",
    description="Show or hide individual pages from the sidebar navigation.",
    icon="layout",
    fields=[
        {"key": "show_dashboard",     "label": "Dashboard",        "type": "toggle", "default": True,  "description": "Widgets and stats at a glance."},
        {"key": "show_social",        "label": "Social Hub",       "type": "toggle", "default": True,  "description": "All your platforms in one view."},
        {"key": "show_notifications", "label": "Notifications",    "type": "toggle", "default": True,  "description": "Aggregated updates from your sources."},
        {"key": "show_email_alias",   "label": "Email Aliases",    "type": "toggle", "default": True,  "description": "Generate and manage email aliases."},
        {"key": "show_portfolio",     "label": "Portfolio",        "type": "toggle", "default": True,  "description": "Projects, work and showcase."},
        {"key": "show_contact",       "label": "Contact",          "type": "toggle", "default": True,  "description": "Get in touch form."},
    ],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_section(section_id: str) -> dict | None:
    return next((s for s in _SECTIONS if s["id"] == section_id), None)


def _build_defaults() -> dict:
    result: dict = {}
    for s in _SECTIONS:
        result[s["id"]] = deepcopy(s["defaults"])
    return result


def _load_overrides() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_overrides(data: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def get_schema() -> list[dict]:
    """Return the full schema (without callables) for the API."""
    out = []
    for s in _SECTIONS:
        out.append({
            "id":          s["id"],
            "label":       s["label"],
            "description": s["description"],
            "icon":        s["icon"],
            "fields":      deepcopy(s["fields"]),
            "defaults":    deepcopy(s["defaults"]),
        })
    return out


def get_active() -> dict:
    """Return merged defaults + file overrides."""
    defaults  = _build_defaults()
    overrides = _load_overrides()
    return _deep_merge(defaults, overrides)


def get_section_values(section_id: str) -> dict:
    active = get_active()
    return active.get(section_id, {})


def save_section(section_id: str, values: dict) -> None:
    """Persist updated values for one section and reload into the app."""
    overrides = _load_overrides()
    overrides[section_id] = values
    _save_overrides(overrides)
    _reload_into_app()


def save_all(data: dict) -> None:
    """Persist an entire config payload and reload into the app."""
    _save_overrides(data)
    _reload_into_app()


def reset() -> None:
    """Delete the override file and reload defaults into the app."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    _reload_into_app()


def validate_section(section_id: str, values: dict) -> list[str]:
    """Return a list of validation error strings (empty = OK)."""
    errors: list[str] = []
    section = _get_section(section_id)
    if section is None:
        return [f"Unknown section: {section_id}"]
    for field in section["fields"]:
        key   = field["key"]
        ftype = field["type"]
        val   = values.get(key)
        if ftype == "url" and val and not val.startswith(("http://", "https://")):
            errors.append(f"'{field['label']}' must be a valid URL starting with http:// or https://.")
        if ftype == "email" and val and "@" not in val:
            errors.append(f"'{field['label']}' must be a valid email address.")
    return errors


def _reload_into_app() -> None:
    """Push the active config into the live process (mutate module globals)."""
    try:
        import app.config as cfg
        active = get_active()

        # ── Identity ─────────────────────────────────────────────────────────
        id_vals = active.get("identity", {})
        cfg.IDENTITY.clear()
        cfg.IDENTITY.update({
            "name":    id_vals.get("name",    "OmniOS Hub"),
            "tagline": id_vals.get("tagline", "Your personal OS for the web"),
            "bio":     id_vals.get("bio",     ""),
            "avatar":  id_vals.get("avatar") or None,
        })

        # ── Social links ─────────────────────────────────────────────────────
        social = active.get("social_links", {})
        new_links = social.get("links", [])
        cfg.SOCIAL_LINKS[:] = new_links

        # ── Notification sources ──────────────────────────────────────────────
        notif = active.get("notifications", {})
        source_map = {
            "github":  ("GitHub",   "api",  notif.get("github_enabled",  True)),
            "youtube": ("YouTube",  "api",  notif.get("youtube_enabled", True)),
            "rss":     ("RSS Feed", "rss",  notif.get("rss_enabled",     False)),
        }
        cfg.NOTIFICATION_SOURCES[:] = [
            {"id": sid, "label": label, "enabled": enabled, "type": stype}
            for sid, (label, stype, enabled) in source_map.items()
        ]

        # ── Pages (visibility) ────────────────────────────────────────────────
        pg = active.get("pages", {})
        _PAGE_DEFS = [
            ("dashboard",     "show_dashboard",     "Dashboard",     "grid",      "/dashboard"),
            ("social",        "show_social",        "Social Hub",    "share-2",   "/social"),
            ("notifications", "show_notifications", "Notifications", "bell",      "/notifications"),
            ("email-alias",   "show_email_alias",   "Email Aliases", "mail",      "/email-alias"),
            ("portfolio",     "show_portfolio",     "Portfolio",     "briefcase", "/portfolio"),
            ("contact",       "show_contact",       "Contact",       "send",      "/contact"),
        ]
        cfg.PAGES[:] = [
            {"id": pid, "label": label, "icon": icon, "route": route}
            for pid, key, label, icon, route in _PAGE_DEFS
            if pg.get(key, True)
        ]
    except Exception:
        pass  # Never break the request cycle due to a reload failure


# Apply overrides on import so that the running app starts with persisted values
_reload_into_app()
