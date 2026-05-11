# OmniOS Hub

**A self-hosted personal web operating system** — a modular, dark-mode dashboard built with Python/Flask and vanilla JavaScript. Manage your identity, social profiles, GitHub activity, notifications, portfolio, email aliases, AI chat, system logs, and configuration snapshots from a single clean interface.

> **Deployment note:** OmniOS Hub is a Python/Flask application with a server-side backend. It **cannot** be deployed to GitHub Pages (which only serves static files). See the [Deployment](#deployment) section for supported hosting platforms.

---

## Features

- **Modular dashboard** — independent pages for every part of your digital life
- **Live GitHub integration** — real-time stats, activity feed, top languages, and public repos
- **Social Hub** — manage all your platform links with full add / edit / delete support
- **Notifications feed** — aggregates GitHub activity and custom RSS feeds in one place
- **Portfolio** — auto-populated from GitHub repos + custom project cards with edit/delete
- **Email Alias manager** — generate and track disposable email aliases (localStorage)
- **AI Assistant** — multi-provider chat (OpenAI, Anthropic, Google Gemini, custom endpoint) with adjustable temperature, max tokens, and system prompt
- **Connections** — unified API key manager for all integrated services; stored securely in `.env`
- **System Logs** — structured activity log for every OmniOS module with category and level filters
- **Config Snapshots** — config version control: capture, label, browse, restore, and delete snapshots; restoring auto-creates a safety backup first
- **Config Editor** — live in-browser editor for all settings (identity, social links, UI preferences, page visibility)
- **Three-layer config system** — factory defaults → user defaults → session overrides
- **Git manager** — configure a remote and push directly from the Settings page
- **Danger Zone** — per-module data wipe and clean-all, registered through a central data registry
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
| AI Assistant | `/ai` | Multi-provider AI chat with provider/model/system-prompt config |
| Connections | `/connections` | Add, update, and remove API keys for all services |
| System Logs | `/logs` | Structured log viewer with category, level, and keyword filters |
| Snapshots | `/snapshots` | Config version control — capture and restore any state |
| Settings | `/settings` | System info, Git config, Default Config Manager, data wipe |
| Config Editor | `/config` | Live editor for all config sections |

---

## Project Structure

```
omnios-hub/
├── main.py                      # Entry point: python3 main.py
├── wsgi.py                      # Gunicorn WSGI entry point
├── requirements.txt             # pip-compatible dependency list
├── pyproject.toml               # PEP 517 project metadata
├── .env.example                 # Template for required environment variables
│
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions: syntax check + startup test
│
├── app/
│   ├── __init__.py              # Flask app factory + context processor
│   ├── config.py                # In-memory config constants (IDENTITY, SOCIAL_LINKS, …)
│   ├── config_manager.py        # Three-layer config system (factory → defaults → overrides)
│   ├── data_registry.py         # Per-module data wipe registry (all modules registered here)
│   ├── git_manager.py           # Git remote / push helpers
│   ├── ai_manager.py            # Multi-provider AI chat (OpenAI / Anthropic / Google / custom)
│   ├── log_manager.py           # Structured JSONL logging
│   ├── snapshot_manager.py      # Config snapshot capture / restore / delete
│   └── routes.py                # All page routes + API endpoints
│
├── templates/
│   ├── base.html                # Shared layout (sidebar, topbar, toast container)
│   ├── index.html               # Home page
│   ├── dashboard.html           # Dashboard widgets
│   ├── social.html              # Social Hub
│   ├── notifications.html       # Notification feed + RSS sources
│   ├── portfolio.html           # GitHub repos + custom projects
│   ├── email_alias.html         # Email alias manager
│   ├── contact.html             # Contact card
│   ├── ai.html                  # AI Assistant (two-panel chat)
│   ├── connections.html         # API key manager
│   ├── logs.html                # System log viewer
│   ├── snapshots.html           # Config snapshot timeline
│   ├── settings.html            # Settings & Default Config Manager
│   └── config.html              # Live Config Editor
│
└── static/
    ├── css/
    │   ├── style.css            # Full design system (variables, components, layout)
    │   └── modules.css          # Page-specific component overrides
    └── js/
        └── core/
            └── os.js            # Shared JS utilities (apiFetch, toast, timeAgo, …)
```

---

## Config System

OmniOS uses a three-layer configuration merge at every request:

```
Factory defaults  (hardcoded in config_manager.py)
        ↓  merged with
User defaults     (.omnios-defaults.json — your saved baseline)
        ↓  merged with
Session overrides (.omnios-config.json — live edits from Config Editor)
        ↓
Active config     (what the app reads and serves to templates)
```

| Action | Effect |
|---|---|
| **Save Changes** (Config Editor) | Writes to `.omnios-config.json` |
| **Save As Default** | Promotes active config to `.omnios-defaults.json`, clears overrides |
| **Reset to Defaults** | Deletes `.omnios-config.json`; falls back to saved defaults (or factory) |
| **Factory Reset** | Deletes both files; returns to hardcoded baseline |

---

## API Reference

### Config

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/config` | Active merged config + schema |
| `POST` | `/api/config` | Save section overrides |
| `POST` | `/api/config/reset` | Reset to defaults |
| `GET` | `/api/config/defaults` | Get defaults manifest |
| `POST` | `/api/config/defaults/save` | Save active config as user defaults |
| `POST` | `/api/config/defaults/delete` | Delete an item from user defaults |
| `POST` | `/api/config/defaults/factory-reset` | Wipe both config files |

### Social Links

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/social-links` | List all configured social links |
| `POST` | `/api/social-links` | Add a new social link |
| `PUT` | `/api/social-links/<index>` | Update a social link by index |
| `DELETE` | `/api/social-links/<index>` | Delete a link |

### GitHub

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/github/<username>` | Public events feed |
| `GET` | `/api/github-stats/<username>` | Repos, stars, followers, top languages, bio |

### AI Assistant

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ai/config` | Get saved AI provider/model config |
| `POST` | `/api/ai/config` | Update AI config |
| `POST` | `/api/ai/chat` | Send a message; returns streamed or full response |

### Connections

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/connections` | List all services with connection status |
| `POST` | `/api/connections` | Add or update an API key for a service |
| `DELETE` | `/api/connections/<service>` | Remove an API key |

### Logs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/logs` | Fetch log entries (query: `category`, `level`, `q`, `limit`) |
| `GET` | `/api/logs/stats` | Aggregate counts by category and level |
| `POST` | `/api/logs/clear` | Delete all log entries |

### Snapshots

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/snapshots` | List all snapshots |
| `POST` | `/api/snapshots` | Capture a new snapshot (optional `label`) |
| `POST` | `/api/snapshots/<id>/restore` | Restore a snapshot (auto-backup first) |
| `DELETE` | `/api/snapshots/<id>` | Delete a snapshot |

### Other

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/rss?url=<url>` | Proxy + parse an RSS/Atom feed |
| `GET` | `/api/identity` | Current identity and social links |
| `GET` | `/api/data/manifest` | List all registered data modules |
| `POST` | `/api/data/wipe` | Wipe all module data (requires `"confirm":"DELETE"`) |
| `GET/POST` | `/api/git/config` | Read or write git configuration |
| `POST` | `/api/git/push` | Push to configured remote |

---

## Getting Started

### Prerequisites

- Python 3.12 or newer
- pip

### Run locally

```bash
# 1. Clone the repository
git clone https://github.com/your-username/omnios-hub.git
cd omnios-hub

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the environment template and fill in your keys
cp .env.example .env
# Edit .env with your favourite editor — at minimum set GITHUB_PAT

# 4. Start the development server
python3 main.py
```

Open [http://localhost:5000](http://localhost:5000).

### Production (Gunicorn)

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2
```

---

## Deployment

OmniOS Hub requires a Python runtime. Choose any of the following:

### Replit (recommended — zero config)

1. Fork or import this repository into [Replit](https://replit.com).
2. Set your secrets in the **Secrets** panel (or use the Connections page inside OmniOS).
3. Click **Run** — Replit detects the Flask app automatically.
4. Hit **Deploy** to get a persistent public URL.

### Render

1. Create a new **Web Service** and connect your GitHub repository.
2. Set **Runtime** to Python 3, **Build Command** to `pip install -r requirements.txt`, and **Start Command** to `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
3. Add your environment variables under **Environment**.
4. Deploy. Render provides a free tier with automatic HTTPS.

### Railway

1. Create a new project from your GitHub repository.
2. Railway auto-detects Python. Set the start command to `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
3. Add environment variables under **Variables**.
4. Deploy.

### Fly.io

```bash
# Install flyctl, then:
fly launch          # auto-detects Python, creates fly.toml
fly secrets set GITHUB_PAT=your_token_here
fly deploy
```

### VPS / self-hosted

```bash
pip install -r requirements.txt
gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2 --daemon
# Optionally put Nginx or Caddy in front for TLS.
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values you need. All variables are optional — OmniOS works without any of them, but GitHub API calls will be rate-limited and AI features will require keys.

| Variable | Description |
|---|---|
| `GITHUB_PAT` | GitHub Personal Access Token — increases API rate limit; required for private repos |
| `OPENAI_API_KEY` | OpenAI API key for the AI Assistant |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API key |
| `GOOGLE_AI_KEY` | Google Gemini API key |
| `CUSTOM_AI_KEY` | Key for any OpenAI-compatible custom endpoint |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key (Notifications feed) |

All keys can also be added and removed live through the **Connections** page without restarting the server.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask |
| Templating | Jinja2 |
| Frontend | Vanilla JavaScript (ES modules, no build step) |
| Styling | CSS3 — custom design system with CSS variables, grid, flexbox |
| Production server | Gunicorn |
| Config persistence | JSON files (`.omnios-*.json`) + `.env` |
| Logging | JSONL (newline-delimited JSON) |
| CI | GitHub Actions |

---

## Contributing

1. Fork the repository and create a feature branch (`git checkout -b feat/my-feature`).
2. Make your changes, keeping style consistent with the existing codebase.
3. Open a pull request — the CI workflow will run a syntax check automatically.

---

## License

MIT — free to use, fork, and self-host.
