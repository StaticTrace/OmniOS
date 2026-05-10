# OmniOS Hub

**A self-hosted personal web operating system** — a modular, dark-mode dashboard built with Python/Flask and vanilla JavaScript. Manage your social profiles, GitHub activity, notifications, portfolio, and email aliases from a single clean interface.

---

## Features

- **Modular dashboard** — independent pages for Social Hub, Notifications, Dashboard, Portfolio, and more
- **Live GitHub integration** — real-time stats, activity feed, top languages, and public repositories
- **Social Hub** — manage all your platform links with full add / edit / delete support
- **Notifications feed** — aggregates GitHub activity and custom RSS feeds in one place
- **Portfolio** — auto-populated from GitHub + custom project cards with edit/delete
- **Email Alias manager** — generate and track disposable email aliases (localStorage)
- **Config Editor** — live in-browser editor for all settings (identity, social links, UI preferences, page visibility)
- **Three-layer config system** — factory defaults → user defaults → session overrides; Reset to Defaults never loses user-saved baseline
- **Default Config Manager** — save your current config as a permanent baseline, delete individual saved items, or factory-reset entirely
- **Git manager** — configure remote, branch, and push directly from the settings page
- **Danger Zone** — per-module data wipe with clean-all support
- **Responsive dark UI** — custom CSS design system with accent colours, modals, toasts, and tag chips

---

## Pages

| Page | Path | Description |
|---|---|---|
| Home | `/` | Profile card, social links, and quick overview |
| Dashboard | `/dashboard` | GitHub stats/activity, quick links, daily focus, live clock |
| Social Hub | `/social` | Platform cards with live GitHub stats; full add/edit/delete |
| Notifications | `/notifications` | Aggregated GitHub events + RSS feed reader |
| Portfolio | `/portfolio` | GitHub repos + custom projects with edit/delete |
| Email Aliases | `/email-alias` | Disposable alias generator and tracker |
| Contact | `/contact` | Contact card with social links |
| Settings | `/settings` | System info, Git config, Default Config Manager, data wipe |
| Config Editor | `/config` | Live editor for all config sections |

---

## Project Structure

```
OmniOS/
├── main.py                    # Entry point: python3 main.py
├── wsgi.py                    # Gunicorn WSGI entry point
│
├── app/
│   ├── __init__.py            # Flask app factory
│   ├── config.py              # In-memory config constants (IDENTITY, SOCIAL_LINKS, …)
│   ├── config_manager.py      # 3-layer config system (factory → defaults → overrides)
│   ├── data_registry.py       # Per-module data wipe registry
│   ├── git_manager.py         # Git remote / push helpers
│   └── routes.py              # All page routes + API endpoints
│
├── templates/
│   ├── base.html              # Shared layout (sidebar, topbar, modals)
│   ├── index.html             # Home page
│   ├── dashboard.html         # Dashboard widgets
│   ├── social.html            # Social Hub (dynamic platform cards)
│   ├── notifications.html     # Notification feed + RSS sources
│   ├── portfolio.html         # GitHub projects + custom projects
│   ├── email_alias.html       # Email alias manager
│   ├── contact.html           # Contact card
│   ├── settings.html          # Settings & Default Config Manager
│   └── config.html            # Live Config Editor
│
├── static/
│   ├── css/
│   │   └── style.css          # Full design system (variables, components, layout)
│   └── js/
│       └── core/
│           └── os.js          # Shared JS utilities (apiFetch, toast, timeAgo, …)
│
├── .omnios-config.json        # Session overrides (auto-generated, gitignored)
└── .omnios-defaults.json      # User-saved baseline (auto-generated, gitignored)
```

---

## Config System

OmniOS uses a three-layer configuration merge at runtime:

```
Factory defaults (hardcoded in config_manager.py)
        ↓  merged with
User defaults (.omnios-defaults.json)
        ↓  merged with
Session overrides (.omnios-config.json)
        ↓
Active config (what the app reads)
```

| Action | Effect |
|---|---|
| **Save Changes** (Config Editor) | Writes to `.omnios-config.json` |
| **Save As Default** | Promotes active config into `.omnios-defaults.json`, clears overrides |
| **Reset to Defaults** | Deletes `.omnios-config.json`; falls back to user defaults (or factory if none) |
| **Factory Reset** | Deletes both files; returns to hardcoded baseline |

---

## API Reference

### Config

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/config` | Returns active merged config + schema |
| `POST` | `/api/config` | Save section overrides |
| `POST` | `/api/config/reset` | Reset to defaults (delete overrides) |
| `GET` | `/api/config/defaults` | Get defaults manifest |
| `POST` | `/api/config/defaults/save` | Save current active config as user defaults |
| `POST` | `/api/config/defaults/delete` | Delete an item from user defaults |
| `POST` | `/api/config/defaults/factory-reset` | Wipe both config files |

### Social Links

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/social-links` | List all configured social links |
| `POST` | `/api/social-links` | Add a new social link |
| `PUT` | `/api/social-links/<index>` | Update a social link by index |
| `DELETE` | `/api/social-links/<index>` | Delete a link (also removes from defaults) |

### GitHub

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/github/<username>` | Public events feed |
| `GET` | `/api/github-stats/<username>` | Repos, stars, followers, top languages, bio |

### Other

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/rss?url=<url>` | Proxy + parse an RSS/Atom feed |
| `GET` | `/api/identity` | Current identity and social links |
| `GET` | `/api/data/manifest` | List all registered data modules |
| `POST` | `/api/data/wipe` | Wipe all module data (requires `"confirm":"DELETE"`) |
| `GET/POST` | `/api/git/config` | Read or write git configuration |
| `POST` | `/api/git/push` | Push to remote |

---

## Getting Started

### Run locally

```bash
# Clone
git clone https://github.com/StaticTrace/OmniOS.git
cd OmniOS

# Install dependencies
pip install flask requests feedparser gunicorn

# Start (development)
python3 main.py
```

Open [http://localhost:5000](http://localhost:5000).

### Production (Gunicorn)

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000
```

---

## Configuration

All settings are managed through the **Config Editor** at `/config`. You can also edit the hardcoded factory defaults directly in `app/config_manager.py`.

### Sections

| Section | Key settings |
|---|---|
| **Identity** | Display name, tagline, bio, avatar URL |
| **Social Links** | Platform name + URL pairs (icon auto-detected from URL) |
| **Notification Sources** | Toggle GitHub, YouTube, RSS feeds |
| **UI Preferences** | GitHub username, weather location, sidebar label |
| **Page Visibility** | Show/hide individual pages from the sidebar |

### Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_PAT` | GitHub Personal Access Token (optional — increases API rate limit) |

---

## Tech Stack

- **Python 3.12 / Flask** — backend, routing, API proxy
- **Jinja2** — server-side templating
- **Vanilla JavaScript** — ES modules, no build step, no framework
- **CSS3** — custom design system with CSS variables, grid, flexbox
- **Gunicorn** — production WSGI server

---

## License

MIT — free to use, fork, and self-host.

---

Made by [@StaticTrace](https://github.com/StaticTrace)
1