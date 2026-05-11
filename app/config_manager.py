"""
OmniOS Config Manager
=====================
Three-layer configuration system:

  1. Factory defaults   – hardcoded in this file (absolute baseline)
  2. User defaults      – .omnios-defaults.json  (user's saved baseline)
  3. Active overrides   – .omnios-config.json    (current session edits)

  Active config = merge(factory → user_defaults → overrides)

Public API:
  get_schema()                        → schema for the Config Editor UI
  get_active()                        → merged active config
  get_defaults_manifest()             → info about user-defined defaults
  save_all(data)                      → persist overrides
  save_as_default()                   → promote active config to user defaults
  delete_from_defaults(...)           → remove item / field from user defaults
  reset()                             → discard overrides (fall back to user defaults)
  factory_reset()                     → wipe both files (full factory state)
  validate_section(section_id, vals)  → list of error strings
  register_section(...)               → module hook to add config sections
"""

import json
import logging
from copy import deepcopy
from pathlib import Path

_log = logging.getLogger(__name__)

BASE_DIR       = Path(__file__).parent.parent
CONFIG_FILE    = BASE_DIR / ".omnios-config.json"    # session overrides
DEFAULTS_FILE  = BASE_DIR / ".omnios-defaults.json"  # user-saved baseline

# ── Section registry ──────────────────────────────────────────────────────────

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
    Register a config section. Call this at module import time.

    field dict keys:
      key, label, type (text|textarea|url|email|toggle|number|select),
      default, description (optional), placeholder (optional),
      options (list[{value,label}], required for select)
    """
    _SECTIONS.append({
        "id":       id,
        "label":    label,
        "description": description,
        "icon":     icon,
        "fields":   fields,
        "defaults": defaults or {f["key"]: f["default"] for f in fields},
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
            "default": "OmniOS Hub", "placeholder": "OmniOS Hub",
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
            "default": "", "placeholder": "https://example.com/avatar.png",
            "description": "Link to a profile image. Leave blank for the default monogram.",
        },
    ],
)

register_section(
    id="social_links",
    label="Social Links",
    description="Platforms shown on your Home card and Social Hub page.",
    icon="share-2",
    fields=[],
    defaults={"links": []},
)

register_section(
    id="notifications",
    label="Notification Sources",
    description="Toggle which sources feed into your Notifications page.",
    icon="bell",
    fields=[
        {
            "key": "github_enabled", "label": "GitHub", "type": "toggle",
            "default": True, "description": "Pull public GitHub activity events.",
        },
        {
            "key": "youtube_enabled", "label": "YouTube", "type": "toggle",
            "default": True, "description": "Show YouTube channel updates.",
        },
        {
            "key": "rss_enabled", "label": "RSS Feed", "type": "toggle",
            "default": False, "description": "Aggregate posts from custom RSS/Atom feeds.",
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
            "key": "github_username", "label": "GitHub Username", "type": "text",
            "default": "", "placeholder": "your-github-username",
            "description": "Used by the GitHub Activity and Stats widgets.",
        },
        {
            "key": "weather_lat", "label": "Weather Latitude", "type": "number",
            "default": "", "placeholder": "e.g. 51.5074",
            "description": "Decimal latitude for the Weather widget.",
        },
        {
            "key": "weather_lon", "label": "Weather Longitude", "type": "number",
            "default": "", "placeholder": "e.g. -0.1278",
            "description": "Decimal longitude for the Weather widget.",
        },
        {
            "key": "sidebar_label", "label": "Sidebar Sub-label", "type": "text",
            "default": "Personal OS", "placeholder": "Personal OS",
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
        {"key": "show_dashboard",     "label": "Dashboard",     "type": "toggle", "default": True,  "description": "Widgets and stats at a glance."},
        {"key": "show_social",        "label": "Social Hub",    "type": "toggle", "default": True,  "description": "All your platforms in one view."},
        {"key": "show_notifications", "label": "Notifications", "type": "toggle", "default": True,  "description": "Aggregated updates from your sources."},
        {"key": "show_email_alias",   "label": "Email Aliases", "type": "toggle", "default": True,  "description": "Generate and manage email aliases."},
        {"key": "show_portfolio",     "label": "Portfolio",     "type": "toggle", "default": True,  "description": "Projects, work and showcase."},
        {"key": "show_contact",       "label": "Contact",       "type": "toggle", "default": True,  "description": "Get in touch form."},
    ],
)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_section(section_id: str) -> dict | None:
    return next((s for s in _SECTIONS if s["id"] == section_id), None)


def _build_factory_defaults() -> dict:
    """Hardcoded defaults — the absolute fallback."""
    return {s["id"]: deepcopy(s["defaults"]) for s in _SECTIONS}


def _load_file(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_file(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (non-destructive)."""
    result = deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


# ── Public read API ───────────────────────────────────────────────────────────

def get_schema() -> list[dict]:
    """Return the full schema list (safe for JSON serialisation)."""
    return [
        {
            "id":          s["id"],
            "label":       s["label"],
            "description": s["description"],
            "icon":        s["icon"],
            "fields":      deepcopy(s["fields"]),
            "defaults":    deepcopy(s["defaults"]),
        }
        for s in _SECTIONS
    ]


def get_active() -> dict:
    """Return merged config: factory → user_defaults → overrides."""
    factory  = _build_factory_defaults()
    user_def = _load_file(DEFAULTS_FILE)
    overrides = _load_file(CONFIG_FILE)
    merged   = _deep_merge(factory, user_def)
    return _deep_merge(merged, overrides)


def get_user_defaults() -> dict:
    """Return the raw user-defined defaults (may be empty)."""
    return _load_file(DEFAULTS_FILE)


def get_section_values(section_id: str) -> dict:
    return get_active().get(section_id, {})


def get_defaults_manifest() -> dict:
    """
    Return a structured manifest of user-defined defaults suitable for the
    Default Config Manager UI. Groups items by section with per-item deletion
    metadata.
    """
    factory  = _build_factory_defaults()
    user_def = _load_file(DEFAULTS_FILE)

    has_user_defaults = bool(user_def)
    sections: list[dict] = []

    for s in _SECTIONS:
        sid  = s["id"]
        if sid not in user_def:
            continue

        section_def  = s
        section_data = user_def[sid]
        items: list[dict] = []

        if sid == "social_links":
            for i, link in enumerate(section_data.get("links", [])):
                items.append({
                    "type":    "list_item",
                    "list_key": "links",
                    "index":   i,
                    "label":   link.get("platform", "Link"),
                    "value":   link.get("url", ""),
                    "icon":    link.get("icon", "link"),
                    "deletable": True,
                })
        else:
            factory_sec = factory.get(sid, {})
            for field in section_def["fields"]:
                key = field["key"]
                if key not in section_data:
                    continue
                val = section_data[key]
                factory_val = factory_sec.get(key)
                display = "on" if val is True else "off" if val is False else str(val)[:60]
                items.append({
                    "type":      "field",
                    "key":       key,
                    "label":     field["label"],
                    "value":     display,
                    "modified":  val != factory_val,
                    "deletable": True,
                })

        if items:
            sections.append({
                "id":    sid,
                "label": s["label"],
                "icon":  s["icon"],
                "items": items,
            })

    return {
        "has_user_defaults": has_user_defaults,
        "sections": sections,
        "defaults_file": str(DEFAULTS_FILE.name),
    }


# ── Public write API ──────────────────────────────────────────────────────────

def save_all(data: dict) -> None:
    """Persist an entire config as overrides and reload into the app."""
    _save_file(CONFIG_FILE, data)
    _reload_into_app()


def save_section(section_id: str, values: dict) -> None:
    overrides = _load_file(CONFIG_FILE)
    overrides[section_id] = values
    _save_file(CONFIG_FILE, overrides)
    _reload_into_app()


def save_as_default() -> None:
    """
    Snapshot the current active config as the user-defined defaults.
    Clears the overrides file so the defaults file becomes the new baseline.
    """
    active = get_active()
    _save_file(DEFAULTS_FILE, active)
    # Clear overrides — the defaults file is now the source of truth
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    _reload_into_app()


def delete_from_defaults(
    section_id: str,
    field_key: str | None = None,
    list_key: str | None = None,
    list_index: int | None = None,
) -> dict:
    """
    Remove a specific item or field from the user defaults file.

    Variants:
      delete_from_defaults("social_links", list_key="links", list_index=0)
          → remove social link at index 0
      delete_from_defaults("identity", field_key="name")
          → revert identity.name to factory default in user defaults
      delete_from_defaults("notifications")
          → remove entire notifications section from user defaults
    """
    user_def = _load_file(DEFAULTS_FILE)

    if section_id not in user_def:
        return {"ok": True, "message": "Section not in user defaults — nothing to delete."}

    if list_key is not None and list_index is not None:
        lst = user_def[section_id].get(list_key, [])
        if 0 <= list_index < len(lst):
            removed = lst.pop(list_index)
            user_def[section_id][list_key] = lst
            msg = f"Removed '{removed.get('platform', list_key)}' from {section_id} defaults."
        else:
            return {"ok": False, "message": "Index out of range."}

    elif field_key is not None:
        if field_key in user_def.get(section_id, {}):
            del user_def[section_id][field_key]
            if not user_def[section_id]:
                del user_def[section_id]
            msg = f"Removed field '{field_key}' from {section_id} defaults."
        else:
            return {"ok": True, "message": "Field not in user defaults — nothing to delete."}

    else:
        del user_def[section_id]
        msg = f"Removed entire section '{section_id}' from user defaults."

    _save_file(DEFAULTS_FILE, user_def)
    _reload_into_app()
    return {"ok": True, "message": msg}


def delete_social_link_by_url(url: str) -> None:
    """Remove a social link from user defaults that matches the given URL."""
    user_def = _load_file(DEFAULTS_FILE)
    if "social_links" not in user_def:
        return
    links = user_def["social_links"].get("links", [])
    new_links = [l for l in links if l.get("url") != url]
    if len(new_links) == len(links):
        return
    user_def["social_links"]["links"] = new_links
    _save_file(DEFAULTS_FILE, user_def)
    _reload_into_app()


def reset() -> None:
    """
    Discard session overrides. Falls back to user-defined defaults
    (or factory defaults if no user defaults file exists).
    """
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    _reload_into_app()


def factory_reset() -> None:
    """
    Full factory reset: wipe both the overrides file and the user defaults
    file. The app returns to its hardcoded baseline.
    """
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
    if DEFAULTS_FILE.exists():
        DEFAULTS_FILE.unlink()
    _reload_into_app()


def validate_section(section_id: str, values: dict) -> list[str]:
    """Return validation error strings (empty list = valid)."""
    errors: list[str] = []
    section = _get_section(section_id)
    if section is None:
        return [f"Unknown section: {section_id}"]
    for field in section["fields"]:
        key   = field["key"]
        ftype = field["type"]
        val   = values.get(key)
        if ftype == "url" and val and not val.startswith(("http://", "https://")):
            errors.append(f"'{field['label']}' must start with http:// or https://.")
        if ftype == "email" and val and "@" not in val:
            errors.append(f"'{field['label']}' must be a valid email address.")
    return errors


# ── Live reload into running process ──────────────────────────────────────────

def _reload_into_app() -> None:
    """Push the active config into live module globals (mutate in place)."""
    try:
        import app.config as cfg
        active = get_active()

        # Identity
        id_vals = active.get("identity", {})
        cfg.IDENTITY.clear()
        cfg.IDENTITY.update({
            "name":    id_vals.get("name",    "OmniOS Hub"),
            "tagline": id_vals.get("tagline", "Your personal OS for the web"),
            "bio":     id_vals.get("bio",     ""),
            "avatar":  id_vals.get("avatar") or None,
        })

        # Social links
        cfg.SOCIAL_LINKS[:] = active.get("social_links", {}).get("links", [])

        # Notification sources
        notif = active.get("notifications", {})
        source_map = {
            "github":  ("GitHub",   "api", notif.get("github_enabled",  True)),
            "youtube": ("YouTube",  "api", notif.get("youtube_enabled", True)),
            "rss":     ("RSS Feed", "rss", notif.get("rss_enabled",     False)),
        }
        cfg.NOTIFICATION_SOURCES[:] = [
            {"id": sid, "label": lbl, "enabled": enabled, "type": stype}
            for sid, (lbl, stype, enabled) in source_map.items()
        ]

        # Pages visibility
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
    except Exception as exc:
        _log.error("_reload_into_app failed: %s", exc, exc_info=True)


# Apply persisted config on first import
_reload_into_app()
