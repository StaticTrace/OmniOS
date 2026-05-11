IDENTITY = {
    "name": "OmniOS Hub",
    "tagline": "Your personal OS for the web",
    "bio": "A private, modular digital operating system built around you — unified profile, dashboard, social hub, notifications, and extensible modules so you can add or remove features as your needs evolve. Clean, minimal UI and a developer-friendly architecture for fast customization.",
    "avatar": None,
}

SOCIAL_LINKS = []

PAGES = [
    {"id": "dashboard",     "label": "Dashboard",      "icon": "grid",           "route": "/dashboard"},
    {"id": "social",        "label": "Social Hub",     "icon": "share-2",        "route": "/social"},
    {"id": "notifications", "label": "Notifications",  "icon": "bell",           "route": "/notifications"},
    {"id": "email-alias",   "label": "Email Aliases",  "icon": "mail",           "route": "/email-alias"},
    {"id": "portfolio",     "label": "Portfolio",      "icon": "briefcase",      "route": "/portfolio"},
    {"id": "contact",       "label": "Contact",        "icon": "send",           "route": "/contact"},
]

NOTIFICATION_SOURCES = [
    {"id": "github",  "label": "GitHub",  "enabled": True,  "type": "api"},
    {"id": "youtube", "label": "YouTube", "enabled": True,  "type": "api"},
    {"id": "rss",     "label": "RSS Feed","enabled": False, "type": "rss"},
]
