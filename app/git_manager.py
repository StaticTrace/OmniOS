import datetime
import json
import os
import subprocess
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / ".omnios-git-config.json"

DEFAULTS = {
    "repo_url": "",
    "username": "",
    "email":    "",
}

# Paths excluded from every push (kept in sync with .gitignore).
# git add -A already respects .gitignore, but we write/refresh the file
# here so the repo always has an authoritative .gitignore regardless of
# whether the user committed one.
_GITIGNORE_CONTENT = """\
# ── Python ────────────────────────────────────────────────────────────────────
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.egg-info/
*.egg
.eggs/

# ── Virtual environments ──────────────────────────────────────────────────────
.venv/
venv/
env/
.pythonlibs/

# ── Build artifacts ───────────────────────────────────────────────────────────
dist/
build/
*.so

# ── JS / Node ─────────────────────────────────────────────────────────────────
node_modules/

# ── Caches ────────────────────────────────────────────────────────────────────
.cache/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.parcel-cache/

# ── Replit internals ──────────────────────────────────────────────────────────
.local/
.agents/
.upm/
replit.nix

# ── Secrets — never commit the live .env (use .env.example for templates) ────
.env

# ── OS / editor noise ─────────────────────────────────────────────────────────
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# ── Project-generated archives ────────────────────────────────────────────────
zipFile.zip
omnios-hub.zip

# NOTE: Everything else — hidden files (.env.example, .omnios* configs,
#       all JSON configs), all module dirs, all backend/frontend files,
#       static assets, templates, and system files — is intentionally
#       included in every push via `git add -A`.
"""


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULTS, **json.loads(CONFIG_FILE.read_text())}
        except Exception:
            pass
    return dict(DEFAULTS)


def save_config(data: dict) -> None:
    cfg = load_config()
    for k in DEFAULTS:
        if k in data:
            cfg[k] = str(data[k]).strip()
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


# ── Subprocess helper ─────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str, env: dict | None = None,
         timeout: int = 60) -> tuple[bool, str]:
    merged_env = {**os.environ, **(env or {})}
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, env=merged_env,
        )
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} s."
    except Exception as exc:
        return False, str(exc)


# ── Ensure .gitignore is present and correct ──────────────────────────────────

def _ensure_gitignore() -> None:
    """Write (or refresh) the .gitignore so excluded paths are always honoured."""
    gitignore_path = BASE_DIR / ".gitignore"
    gitignore_path.write_text(_GITIGNORE_CONTENT)


# ── Error classifier ──────────────────────────────────────────────────────────

def _classify(raw: str, pat: str = "") -> str:
    """Turn a raw git error into a user-friendly message."""
    safe = raw.replace(pat, "***") if pat else raw
    low  = raw.lower()
    if any(w in low for w in ("authentication failed", "bad credentials",
                               "invalid username", "403", "401",
                               "could not authenticate")):
        return (
            "Authentication failed — your GitHub PAT may have expired or is "
            "missing the 'repo' scope.\n\nDetails: " + safe
        )
    if "repository not found" in low or "could not read from remote" in low:
        return (
            "Repository not found — check the remote URL and that your PAT "
            "has access to this repository.\n\nDetails: " + safe
        )
    if "permission denied" in low:
        return (
            "Permission denied — ensure your PAT has write ('repo') access.\n\n"
            "Details: " + safe
        )
    if "rejected" in low and "fetch first" in low:
        return (
            "Remote has commits that could not be synced automatically. "
            "A safe reset was attempted but the push was still rejected.\n\n"
            "Details: " + safe
        )
    if "rejected" in low:
        return "Push rejected by the remote.\n\nDetails: " + safe
    if any(w in low for w in ("corrupt", "missing object", "bad object",
                               "loose object")):
        return (
            "Remote repository appears corrupted or has missing objects. "
            "Try deleting and recreating the remote repository.\n\nDetails: " + safe
        )
    return safe


# ── Main push function ────────────────────────────────────────────────────────

def git_push() -> dict:
    cfg = load_config()
    pat = os.environ.get("GITHUB_PAT", "").strip()

    # ── Pre-flight checks ──────────────────────────────────────────────────
    errors: list[str] = []
    if not cfg["repo_url"]: errors.append("Repo URL is not set.")
    if not cfg["username"]: errors.append("Git username is not set.")
    if not cfg["email"]:    errors.append("Git email is not set.")
    if not pat:             errors.append("GITHUB_PAT secret is not set.")
    if errors:
        return {"success": False,
                "message": "Configuration incomplete:\n• " + "\n• ".join(errors)}

    # Inject PAT into HTTPS URL
    repo_url = cfg["repo_url"].strip()
    if "github.com" in repo_url:
        repo_url = repo_url.replace("https://",
                                    f"https://{cfg['username']}:{pat}@")

    cwd   = str(BASE_DIR)
    steps: list[str] = []

    # ── 1. Ensure .gitignore is authoritative ──────────────────────────────
    _ensure_gitignore()
    steps.append("✦ .gitignore refreshed — full OmniOS codebase will be staged.")

    # ── 2. Init ────────────────────────────────────────────────────────────
    if not (BASE_DIR / ".git").exists():
        ok, out = _run(["git", "init"], cwd)
        steps.append(f"✦ git init: {out}")
        if not ok:
            return {"success": False, "message": "\n".join(steps)}
        # Set default branch to main for fresh repos
        _run(["git", "checkout", "-b", "main"], cwd)

    # ── 3. Identity ────────────────────────────────────────────────────────
    _run(["git", "config", "user.name",  cfg["username"]], cwd)
    _run(["git", "config", "user.email", cfg["email"]],    cwd)
    steps.append(f"✦ Identity: {cfg['username']} <{cfg['email']}>")

    # ── 4. Remote ──────────────────────────────────────────────────────────
    ok, _ = _run(["git", "remote", "get-url", "origin"], cwd)
    if ok:
        _run(["git", "remote", "set-url", "origin", repo_url], cwd)
    else:
        _run(["git", "remote", "add", "origin", repo_url], cwd)
    steps.append("✦ Remote configured.")

    # ── 5. Determine branch ────────────────────────────────────────────────
    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    branch = branch.strip() or "main"

    # ── 6. Fetch remote refs ───────────────────────────────────────────────
    ok, fetch_out = _run(["git", "fetch", "--all", "--prune"], cwd, timeout=30)
    if ok:
        steps.append(f"✦ git fetch --all: {fetch_out or 'up to date'}")
    else:
        steps.append(f"⚠ git fetch skipped: {fetch_out or 'could not reach remote'}")

    # ── 7. Safe sync (only if remote branch exists) ────────────────────────
    remote_ref = f"origin/{branch}"
    _, ref_check = _run(["git", "rev-parse", "--verify", remote_ref], cwd)
    remote_exists = bool(ref_check and not ref_check.startswith("fatal"))

    if remote_exists:
        # Try fast-forward merge first (safe, non-destructive)
        ff_ok, ff_out = _run(["git", "merge", "--ff-only", remote_ref], cwd)
        if ff_ok:
            steps.append(f"✦ Fast-forward merge: {ff_out or 'already up to date'}")
        else:
            # Diverged: reset our working tree onto the remote HEAD,
            # keeping all local changes staged (--soft)
            steps.append(
                f"⚠ Fast-forward failed "
                f"({ff_out.splitlines()[0] if ff_out else 'diverged'}) "
                f"— running safe reset (--soft)."
            )
            ok, reset_out = _run(["git", "reset", "--soft", remote_ref], cwd)
            if ok:
                steps.append(f"✦ git reset --soft {remote_ref}: {reset_out or 'done'}")
            else:
                steps.append(f"⚠ Reset warning: {reset_out}")

    # ── 8. Stage entire OmniOS codebase ───────────────────────────────────
    # git add -A stages all tracked + untracked files (including hidden files
    # like .env.example, .omnios* configs, all JSON, all module dirs, etc.)
    # and respects .gitignore to exclude secrets and build artifacts.
    ok, add_out = _run(["git", "add", "-A"], cwd)
    steps.append(f"✦ git add -A (full codebase): {add_out or 'all files staged'}")
    if not ok:
        return {"success": False, "message": "\n".join(steps)}

    # ── 9. Check for changes ───────────────────────────────────────────────
    _, status_out = _run(["git", "status", "--porcelain"], cwd)
    if not status_out and remote_exists:
        steps.append("✦ Nothing new to commit — remote is already up to date.")
        return {"success": True, "message": "\n".join(steps)}

    # Show a short summary of what's being committed
    _, diff_stat = _run(["git", "diff", "--cached", "--stat"], cwd)
    if diff_stat:
        steps.append(f"✦ Staged changes:\n{diff_stat}")

    # ── 10. Commit ─────────────────────────────────────────────────────────
    commit_msg = (
        f"OmniOS full-codebase push — "
        f"{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    ok, commit_out = _run(["git", "commit", "-m", commit_msg], cwd)
    steps.append(f"✦ git commit: {commit_out}")
    if not ok and "nothing to commit" not in commit_out.lower():
        return {"success": False, "message": "\n".join(steps)}

    # ── 11. Push (force-with-lease first, fallback to --force) ─────────────
    # --force-with-lease only overwrites if the remote ref matches what we
    # fetched, making it safe against concurrent pushes.
    ok, push_out = _run(
        ["git", "push", "-u", "origin", branch, "--force-with-lease"],
        cwd, timeout=90,
    )
    steps.append(f"✦ git push --force-with-lease → {branch}: {push_out or 'success'}")

    if ok:
        return {"success": True, "message": "\n".join(steps)}

    # force-with-lease was rejected (remote moved since our fetch)
    # Fall back to --force as a last resort, with a clear note in the log.
    steps.append("⚠ force-with-lease rejected — retrying with --force.")
    ok, push_out2 = _run(
        ["git", "push", "-u", "origin", branch, "--force"],
        cwd, timeout=90,
    )
    safe_out2 = push_out2.replace(pat, "***") if pat else push_out2
    steps.append(f"✦ git push --force → {branch}: {safe_out2 or 'success'}")

    if ok:
        return {"success": True, "message": "\n".join(steps)}

    # Both pushes failed — classify the error for a clear UI message
    final_err = _classify(push_out2 or push_out, pat)
    return {
        "success": False,
        "message": "\n".join(steps[:-1]) + f"\n\n✖ Push failed:\n{final_err}",
    }
