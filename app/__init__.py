from pathlib import Path
from flask import Flask


def create_app() -> Flask:
    # Load .env if it exists (persists GITHUB_PAT and other secrets)
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file, override=False)
        except ImportError:
            pass

    app = Flask(__name__, static_folder="../static", template_folder="../templates")

    from .routes import register_routes
    register_routes(app)
    return app
