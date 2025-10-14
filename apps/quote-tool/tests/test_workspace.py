from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Blueprint, Flask


def _load_workspace_module():
    """Import and return the quote tool workspace module safely."""

    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))

    existing = sys.modules.get("app")
    module_path = Path(getattr(existing, "__file__", "")) if existing else None
    if module_path and "hana-inventory" in module_path.parts:
        sys.modules.pop("app", None)

    return importlib.import_module("app.workspace")


def _build_test_app() -> Flask:
    """Return a minimal Flask app wired with the workspace blueprint."""

    workspace_module = _load_workspace_module()
    workspace_blueprint = workspace_module.workspace_bp
    template_dir = Path(__file__).resolve().parents[1] / "templates"
    app = Flask(__name__, template_folder=str(template_dir))
    app.config.update(
        SECRET_KEY="testing",
        TESTING=True,
        LOGIN_DISABLED=True,
    )
    app.jinja_env.globals.setdefault("fsi_theme", lambda: "")

    anonymous_user = SimpleNamespace(
        is_authenticated=False,
        role="",
        is_admin=False,
        employee_approved=False,
        first_name=None,
        email="tester@example.com",
        name="Test User",
    )

    @app.context_processor
    def _inject_current_user():  # pragma: no cover - trivial template helper
        return {"current_user": anonymous_user}

    theme_static_path = Path(__file__).resolve().parents[1] / "theme"
    theme_bp = Blueprint(
        "theme",
        __name__,
        static_folder=str(theme_static_path),
        static_url_path="/theme",
    )
    app.register_blueprint(theme_bp)

    @app.route("/quotes/new")
    def quotes_new() -> str:  # pragma: no cover - trivial stub
        return "quotes"

    @app.route("/help", endpoint="help.help_index")
    def help_index() -> str:  # pragma: no cover - trivial stub
        return "help"

    app.register_blueprint(workspace_blueprint)
    return app, workspace_module


def test_normalize_app_entries_resolves_endpoints():
    """Entries with ``endpoint`` should resolve to URLs and mark as internal."""

    app, workspace_module = _build_test_app()
    with app.test_request_context():
        entries = workspace_module._normalize_app_entries(
            [
                {
                    "slug": "quote-tool",
                    "name": "Quote Tool",
                    "description": "Build quotes",
                    "endpoint": "quotes_new",
                }
            ]
        )
    assert len(entries) == 1
    entry = entries[0]
    assert entry.url == "/quotes/new"
    assert entry.external is False
    assert entry.primary is False
    assert entry.cta_label == "Open"


def test_workspace_home_renders_configured_apps():
    """The workspace view should render configured applications."""

    app, workspace_module = _build_test_app()
    app.config["WORKSPACE_APPS"] = [
        {
            "slug": "quote-tool",
            "name": "Quote Tool",
            "description": "Primary app",
            "endpoint": "quotes_new",
            "primary": True,
            "cta_label": "Start quoting",
        },
        {
            "slug": "expenses",
            "name": "Expense Reports",
            "description": "Submit receipts",
            "url": "https://expenses.example.com",
            "cta_label": "Open expenses",
            "external": True,
        },
    ]

    client = app.test_client()
    response = client.get("/workspace/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Quote Tool" in html
    assert "Start quoting" in html
    assert "Expense Reports" in html
    assert "https://expenses.example.com" in html
