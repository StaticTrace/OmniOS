# OmniWeb

**A lightweight personal website & dashboard template** built with pure HTML, CSS, and Vanilla JavaScript — no frameworks, no build tools.

## Features

- **Dark / Light mode** with localStorage persistence
- **Fully responsive** — mobile-first layout
- **11 live dashboard widgets** — clock, weather, focus, to-do, quick links, analytics, GitHub activity, journal, habit tracker, Pomodoro timer, and free Steam games
- **5 browser tools** — text counter, password generator, name generator, calculator, JSON formatter
- **Local Vault** — private notes stored in your browser (never sent anywhere)
- **PWA-ready** — service worker with update banner
- **Accessible** — semantic HTML and ARIA labels throughout

## Project Structure

```
OmniWeb/
├── index.html              # Home
├── about.html
├── projects.html
├── contact.html
├── dashboard.html          # Live widgets dashboard
├── tools.html              # Browser-side tools
├── vault.html              # Private notes
├── style.css               # All styles (no build step)
│
├── js/
│   ├── utils.js            # Shared utilities (escHtml, timeAgo, storage, …)
│   ├── core.js             # Site-wide init (dark mode, SW, nav, animations)
│   ├── widgets/
│   │   ├── time.js
│   │   ├── weather.js
│   │   ├── focus.js
│   │   ├── todo.js
│   │   ├── quick-links.js
│   │   ├── analytics.js
│   │   ├── github.js
│   │   ├── journal.js
│   │   ├── habit.js
│   │   ├── pomodoro.js
│   │   └── steam.js
│   ├── tools/
│   │   ├── toast.js
│   │   ├── text-counter.js
│   │   ├── password.js
│   │   ├── namegen.js
│   │   ├── calculator.js
│   │   └── json-formatter.js
│   └── pages/              # Entry points (one per HTML page)
│       ├── home.js
│       ├── dashboard.js
│       ├── tools-page.js
│       └── vault.js
│
├── app/                    # Flask backend (Python)
│   ├── __init__.py         # App factory
│   ├── config.py           # Constants and headers
│   ├── routes.py           # Static serving + API routes
│   └── scrapers/
│       ├── steamdb.py      # SteamDB scraper (cloudscraper)
│       └── steam_store.py  # Steam Store fallback
├── main.py                 # Entry point: python3 main.py
│
├── manifest.json
├── sw.js
├── favicon.svg
├── robots.txt
└── sitemap.xml
```

## Getting Started

### Run locally

```bash
# Clone
git clone https://github.com/StaticTrace/OmniWeb.git
cd OmniWeb

# Install Python dependencies
pip install flask cloudscraper beautifulsoup4 lxml requests

# Start
python3 main.py
```

Open [http://localhost:5000](http://localhost:5000).

## Dashboard Widgets

| Widget | Description |
|---|---|
| Time | Live clock with date |
| Weather | Current conditions via Open-Meteo (no API key needed) |
| Daily Focus | One-sentence intention, persisted per day |
| To-Do List | Persistent task list with done/delete |
| Quick Links | Customisable bookmark grid (add/remove) |
| Site Analytics | Client-side page-view and session tracking |
| GitHub Activity | Live public event feed for any username |
| Daily Journal | Day-by-day notes with auto-save and word count |
| Habit Tracker | Streaks and 7-day history per habit |
| Pomodoro Timer | Focus/break modes with audio + notifications |
| Free Steam Games | Live feed of free-to-keep and free-weekend games |

## Browser Tools

| Tool | Description |
|---|---|
| Text Counter | Words, characters, lines, estimated read time |
| Password Generator | Cryptographically strong, configurable length/charset |
| Name Generator | Username, full name, and code-name modes |
| Calculator | Standard operations, clean grid UI |
| JSON Formatter | Format, minify, and copy JSON |

## Customisation

- **Colours & layout** — edit the CSS custom properties at the top of `style.css`
- **GitHub username** — change `GITHUB_USERNAME` in `js/core.js`
- **Weather location** — update the lat/lon in `js/widgets/weather.js`
- **Add a widget** — create `js/widgets/your-widget.js` exporting `init()`, import it in `js/pages/dashboard.js`
- **Add a tool** — create `js/tools/your-tool.js`, import it in `js/pages/tools-page.js`

## Tech Stack

- HTML5 (semantic markup)
- CSS3 (custom properties, grid, flexbox)
- Vanilla JavaScript — ES modules, no transpiler
- Python / Flask — lightweight static server + Steam API proxy

## License

MIT — free to use for personal or commercial projects.

---

Made with by [@StaticTrace](https://github.com/StaticTrace)
