import io, os, hashlib, time, zipfile, requests, sys, platform
from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory, request, send_file
from .config import IDENTITY, SOCIAL_LINKS, PAGES, NOTIFICATION_SOURCES
from .git_manager import load_config as git_load, save_config as git_save, git_push
from .data_registry import run_all_cleaners
from . import config_manager as _cfg_mgr

_DOTENV = Path(__file__).parent.parent / ".env"


def _write_secret(key: str, value: str) -> None:
    """Persist a secret to the project .env file and inject into current process env."""
    lines: list[str] = []
    if _DOTENV.exists():
        lines = _DOTENV.read_text().splitlines()
    # Remove any existing entry for this key
    lines = [l for l in lines if not l.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    _DOTENV.write_text("\n".join(lines) + "\n")
    os.environ[key] = value  # available immediately in this process

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def register_routes(app: Flask) -> None:

    # ── Page routes ──────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("index.html", identity=IDENTITY, social_links=SOCIAL_LINKS, pages=PAGES)

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html", identity=IDENTITY, pages=PAGES)

    @app.route("/social")
    def social():
        return render_template("social.html", identity=IDENTITY, social_links=SOCIAL_LINKS, pages=PAGES)

    @app.route("/notifications")
    def notifications():
        return render_template("notifications.html", identity=IDENTITY, sources=NOTIFICATION_SOURCES, pages=PAGES)

    @app.route("/email-alias")
    def email_alias():
        return render_template("email_alias.html", identity=IDENTITY, pages=PAGES)

    @app.route("/portfolio")
    def portfolio():
        return render_template("portfolio.html", identity=IDENTITY, pages=PAGES)

    @app.route("/contact")
    def contact():
        return render_template("contact.html", identity=IDENTITY, pages=PAGES)

    @app.route("/settings")
    def settings():
        import subprocess, platform as pf
        try:
            git_v = subprocess.check_output(["git", "--version"], text=True).strip()
        except Exception:
            git_v = "not found"
        system = {
            "Python":    sys.version.split()[0],
            "Platform":  pf.system() + " " + pf.release(),
            "Git":       git_v,
            "GITHUB_PAT": "set ✓" if os.environ.get("GITHUB_PAT") else "not set",
        }
        return render_template("settings.html", identity=IDENTITY, pages=PAGES, system=system)

    # ── API: Identity ─────────────────────────────────────────────────────────

    @app.route("/api/identity")
    def api_identity():
        return jsonify({"identity": IDENTITY, "social_links": SOCIAL_LINKS})

    # ── API: Git config ───────────────────────────────────────────────────────

    @app.route("/api/git/config", methods=["GET", "POST"])
    def api_git_config():
        if request.method == "GET":
            cfg = git_load()
            cfg["has_pat"] = bool(os.environ.get("GITHUB_PAT", "").strip())
            return jsonify(cfg)

        data = request.get_json(silent=True) or {}
        # Save non-sensitive fields to JSON config
        git_save(data)
        # If a PAT was provided, write it to the environment file
        pat = data.get("pat", "").strip()
        if pat:
            _write_secret("GITHUB_PAT", pat)
        return jsonify({"ok": True})

    # ── API: Git push ─────────────────────────────────────────────────────────

    @app.route("/api/git/push", methods=["POST"])
    def api_git_push():
        result = git_push()
        return jsonify(result)

    # ── API: Data manifest ────────────────────────────────────────────────────

    @app.route("/api/data/manifest")
    def api_data_manifest():
        from .data_registry import get_manifest
        return jsonify({"modules": get_manifest()})

    # ── API: Data wipe ────────────────────────────────────────────────────────

    @app.route("/api/data/wipe", methods=["POST"])
    def api_data_wipe():
        data = request.get_json(silent=True) or {}
        if data.get("confirm") != "DELETE":
            return jsonify({"ok": False, "error": "Confirmation phrase missing or incorrect."}), 400
        result = run_all_cleaners()
        return jsonify(result)

    # ── API: GitHub activity ──────────────────────────────────────────────────

    @app.route("/api/github/<username>")
    def api_github(username):
        try:
            r = requests.get(
                f"https://api.github.com/users/{username}/events/public",
                headers={"Accept": "application/vnd.github+json"},
                timeout=8,
            )
            if r.status_code != 200:
                return jsonify({"error": f"GitHub API {r.status_code}", "events": []})
            events = r.json()[:10]
            return jsonify({"events": events, "error": None})
        except Exception as e:
            return jsonify({"error": str(e), "events": []})

    @app.route("/api/github-stats/<username>")
    def api_github_stats(username):
        try:
            u = requests.get(f"https://api.github.com/users/{username}", timeout=8)
            if u.status_code != 200:
                return jsonify({"error": "not found"})
            data = u.json()
            repos_r = requests.get(
                f"https://api.github.com/users/{username}/repos?per_page=100",
                timeout=8,
            )
            repos = repos_r.json() if repos_r.status_code == 200 else []
            total_stars = sum(r.get("stargazers_count", 0) for r in repos)
            top_langs = {}
            for repo in repos[:20]:
                lang = repo.get("language")
                if lang:
                    top_langs[lang] = top_langs.get(lang, 0) + 1
            top_langs = sorted(top_langs.items(), key=lambda x: -x[1])[:5]
            return jsonify({
                "username":   data.get("login"),
                "name":       data.get("name"),
                "avatar":     data.get("avatar_url"),
                "bio":        data.get("bio"),
                "followers":  data.get("followers", 0),
                "following":  data.get("following", 0),
                "repos":      data.get("public_repos", 0),
                "stars":      total_stars,
                "top_langs":  top_langs,
                "url":        data.get("html_url"),
                "error":      None,
            })
        except Exception as e:
            return jsonify({"error": str(e)})

    # ── API: RSS feed proxy ───────────────────────────────────────────────────

    @app.route("/api/rss")
    def api_rss():
        feed_url = request.args.get("url", "")
        if not feed_url:
            return jsonify({"error": "Missing url param", "items": []})
        try:
            r = requests.get(feed_url, timeout=10, headers={"User-Agent": "OmniOS/1.0"})
            r.raise_for_status()
            from xml.etree import ElementTree as ET
            root = ET.fromstring(r.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items = []
            for item in (root.findall(".//item") or root.findall(".//atom:entry", ns))[:15]:
                def text(tag):
                    el = item.find(tag) or item.find(f"atom:{tag}", ns)
                    return el.text.strip() if el is not None and el.text else ""
                items.append({
                    "title":   text("title"),
                    "link":    text("link"),
                    "pubDate": text("pubDate") or text("updated"),
                    "summary": text("description") or text("summary"),
                })
            return jsonify({"items": items, "error": None})
        except Exception as e:
            return jsonify({"error": str(e), "items": []})

    # ── API: Email alias (stateless placeholder) ──────────────────────────────

    @app.route("/api/alias/generate", methods=["POST"])
    def api_alias_generate():
        data  = request.get_json(silent=True) or {}
        label = data.get("label", "").strip().lower().replace(" ", "-") or "alias"
        seed  = f"{label}-{time.time()}"
        h     = hashlib.sha1(seed.encode()).hexdigest()[:8]
        alias = f"{label}-{h}@omnios.hub"
        return jsonify({"alias": alias, "label": label, "created": int(time.time())})

    @app.route("/api/alias/check", methods=["POST"])
    def api_alias_check():
        data  = request.get_json(silent=True) or {}
        alias = data.get("alias", "")
        return jsonify({"alias": alias, "active": True, "messages": 0})

    # ── Export: ZIP the entire project ────────────────────────────────────────

    EXCLUDE_DIRS = {
        ".git", ".pythonlibs", "__pycache__", ".cache", ".local",
        "node_modules", ".agents", "dist", "build", ".venv", "venv",
        ".mypy_cache", ".pytest_cache", ".ruff_cache",
    }
    EXCLUDE_FILES = {".DS_Store", ".env"}
    EXCLUDE_EXTS  = {".pyc", ".pyo", ".pyd"}

    @app.route("/api/export-zip")
    def api_export_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for root, dirs, files in os.walk(BASE_DIR):
                dirs[:] = [
                    d for d in dirs
                    if d not in EXCLUDE_DIRS and not d.startswith(".")
                ]
                for fname in files:
                    if fname in EXCLUDE_FILES:
                        continue
                    if any(fname.endswith(ext) for ext in EXCLUDE_EXTS):
                        continue
                    full_path = os.path.join(root, fname)
                    arc_path  = os.path.relpath(full_path, BASE_DIR)
                    try:
                        zf.write(full_path, arc_path)
                    except (OSError, PermissionError):
                        pass
        buf.seek(0)
        return send_file(
            buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name="omnios-hub.zip",
        )

    # ── Config Editor page ────────────────────────────────────────────────────

    @app.route("/config")
    def config_editor():
        return render_template("config.html", identity=IDENTITY, pages=PAGES)

    # ── API: Config schema + active values ────────────────────────────────────

    @app.route("/api/config")
    def api_config_get():
        return jsonify({
            "schema": _cfg_mgr.get_schema(),
            "active": _cfg_mgr.get_active(),
        })

    # ── API: Save config ──────────────────────────────────────────────────────

    @app.route("/api/config", methods=["POST"])
    def api_config_save():
        payload = request.get_json(silent=True) or {}
        data    = payload.get("data", {})
        errors: list[str] = []
        schema  = _cfg_mgr.get_schema()
        for section in schema:
            sid = section["id"]
            if sid in data:
                errs = _cfg_mgr.validate_section(sid, data[sid])
                errors.extend(errs)
        if errors:
            return jsonify({"ok": False, "errors": errors}), 400
        _cfg_mgr.save_all(data)
        # Refresh the module-level names used by template routes
        global IDENTITY, SOCIAL_LINKS, PAGES, NOTIFICATION_SOURCES
        from .config import IDENTITY, SOCIAL_LINKS, PAGES, NOTIFICATION_SOURCES
        return jsonify({"ok": True})

    # ── API: Reset config to defaults ─────────────────────────────────────────

    @app.route("/api/config/reset", methods=["POST"])
    def api_config_reset():
        _cfg_mgr.reset()
        global IDENTITY, SOCIAL_LINKS, PAGES, NOTIFICATION_SOURCES
        from .config import IDENTITY, SOCIAL_LINKS, PAGES, NOTIFICATION_SOURCES
        return jsonify({"ok": True})

    # ── Favicon ───────────────────────────────────────────────────────────────

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")

    # ── Static fallback ───────────────────────────────────────────────────────

    @app.route("/static/<path:path>")
    def static_files(path):
        return send_from_directory(os.path.join(BASE_DIR, "static"), path)
