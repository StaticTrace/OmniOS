from pathlib import Path
from flask import Flask


def create_app() -> Flask:
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

    @app.context_processor
    def _inject_globals() -> dict:
        """Inject identity, social_links, pages, and ui config into every template."""
        from .config import IDENTITY, SOCIAL_LINKS, PAGES
        from . import config_manager as _cm
        ui = _cm.get_section_values("ui")
        return dict(
            identity=IDENTITY,
            social_links=SOCIAL_LINKS,
            pages=PAGES,
            sidebar_label=ui.get("sidebar_label", "Personal OS"),
        )

    return app
