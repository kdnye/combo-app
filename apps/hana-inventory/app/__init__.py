from flask import Flask

from .config import Config
from .models import db
from .routes import bp as main_bp
from .data_loader import seed_database


def create_app(config_class: type[Config] | None = None) -> Flask:
    """Application factory for the inventory dashboard."""
    app = Flask(__name__)
    app.config.from_object(config_class or Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_database()

    app.register_blueprint(main_bp)
    return app


__all__ = ["create_app", "db"]
