# app/__init__.py
from flask import (
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import LoginManager, current_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from datetime import datetime
import os
import smtplib
from email.message import EmailMessage
from jinja2 import TemplateNotFound
from sqlalchemy import inspect
from typing import Optional, Union
from flask.typing import ResponseReturnValue

from quote.distance import get_distance_miles
from quote.theme import init_fsi_theme
from .models import db, User, Quote, HotshotRate
from services.mail import (
    MailRateLimitError,
    enforce_mail_rate_limit,
    log_email_dispatch,
    validate_sender_domain,
    user_has_mail_privileges,
)
from services.settings import load_mail_settings, reload_overrides

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def build_map_html(origin_zip: str, destination_zip: str) -> str | None:
    """Return an embedded Google Maps iframe for the given ZIP codes.

    Returns ``None`` if the API key is missing or the ZIPs are invalid.
    """
    key = current_app.config.get("GOOGLE_MAPS_API_KEY") or os.getenv(
        "GOOGLE_MAPS_API_KEY"
    )
    if not key:
        return None

    o = "".join(ch for ch in str(origin_zip).strip() if ch.isdigit())
    d = "".join(ch for ch in str(destination_zip).strip() if ch.isdigit())
    if len(o) != 5 or len(d) != 5:
        return None

    src = (
        "https://www.google.com/maps/embed/v1/directions"
        f"?key={key}&origin={o},USA&destination={d},USA"
    )
    return (
        '<iframe width="600" height="450" style="border:0" '
        f'loading="lazy" allowfullscreen src="{src}"></iframe>'
    )


def send_email(
    to: str,
    subject: str,
    body: str,
    *,
    feature: str = "general",
    user: Optional[User] = None,
) -> None:
    """Send an email using SMTP after enforcing safety policies.

    Args:
        to: Recipient email address.
        subject: Message subject line.
        body: Plain-text message body.
        feature: Short label identifying the caller (for example,
            ``"password_reset"``). Used by
            :func:`services.mail.enforce_mail_rate_limit` to track usage.
        user: Authenticated :class:`~app.models.User` requesting the send, if
            available. Enables per-user throttles.

    Raises:
        MailRateLimitError: When rate limits configured in
            :mod:`services.mail` are exceeded.
        ValueError: If ``MAIL_DEFAULT_SENDER`` is configured for a domain
            outside ``MAIL_ALLOWED_SENDER_DOMAIN``.
        smtplib.SMTPException: If the underlying SMTP call fails.

    External dependencies:
        * Applies :func:`services.mail.enforce_mail_rate_limit` and
          :func:`services.mail.log_email_dispatch` around SMTP activity.
        * Reads runtime overrides with :func:`services.settings.load_mail_settings`.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    default_sender = current_app.config.get(
        "MAIL_DEFAULT_SENDER", "quote@freightservices.net"
    )
    validate_sender_domain(default_sender)
    msg["From"] = default_sender
    msg["To"] = to
    msg.set_content(body)
    enforce_mail_rate_limit(feature, user, to)
    overrides = load_mail_settings()
    server = overrides.server or current_app.config.get("MAIL_SERVER", "localhost")
    configured_port = current_app.config.get("MAIL_PORT", 0) or None
    port = overrides.port if overrides.port is not None else configured_port
    use_tls = (
        overrides.use_tls
        if overrides.use_tls is not None
        else current_app.config.get("MAIL_USE_TLS")
    )
    use_ssl = (
        overrides.use_ssl
        if overrides.use_ssl is not None
        else current_app.config.get("MAIL_USE_SSL")
    )
    username = overrides.username or current_app.config.get("MAIL_USERNAME")
    password = overrides.password or current_app.config.get("MAIL_PASSWORD")

    if use_ssl:
        smtp_cls = smtplib.SMTP_SSL
        default_port = 465
    else:
        smtp_cls = smtplib.SMTP
        default_port = 587 if use_tls else 25

    with smtp_cls(server, port or default_port) as smtp:
        if use_tls and not use_ssl:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)
    log_email_dispatch(feature, user, to)


def _verify_app_setup(app: Flask) -> list[str]:
    """Check for required database tables and templates.

    Args:
        app: The active :class:`~flask.Flask` application.

    Returns:
        A list of human-readable error messages describing missing
        resources. Uses :func:`sqlalchemy.inspect` to inspect database
        tables and :mod:`jinja2` to look up templates.
    """
    errors: list[str] = []
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    required_tables = {
        User.__tablename__,
        Quote.__tablename__,
        HotshotRate.__tablename__,
    }
    for table in required_tables:
        if table not in existing_tables:
            errors.append(f"Missing table: {table}")

    required_templates = ["index.html", "map.html", "new_quote.html", "500.html"]
    for tmpl in required_templates:
        try:
            app.jinja_env.get_or_select_template(tmpl)
        except TemplateNotFound:
            errors.append(f"Missing template: {tmpl}")

    return errors


def create_app(config_class: Union[str, type] = "config.Config") -> Flask:
    """Application factory for the quote tool.

    Args:
        config_class: Import path or class used to configure the app.

    Returns:
        A fully initialized :class:`~flask.Flask` application.
    """
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    init_fsi_theme(app)

    # Ensure database tables exist before handling requests. When BigQuery is
    # configured this will also provision the dataset and missing tables so the
    # application persists data in BigQuery instead of SQLite.
    from db import ensure_database_schema  # Local import avoids circular imports.

    with app.app_context():
        ensure_database_schema(db.engine)
        setup_errors = _verify_app_setup(app)
        reload_overrides(app)

    limiter.init_app(app)

    if setup_errors:
        message = "; ".join(setup_errors)
        app.logger.error("Application setup failed: %s", message)

        @app.before_request
        def _setup_failed() -> tuple[str, int]:
            return (
                render_template("500.html", message="Application is misconfigured."),
                500,
            )

    # Blueprints
    from .auth import auth_bp
    from .admin import admin_bp
    from .help import help_bp
    from .quotes import quotes_bp
    from quote.admin_view import admin_quotes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(admin_quotes_bp, url_prefix="/admin")
    app.register_blueprint(quotes_bp, url_prefix="/quotes")
    app.register_blueprint(help_bp, url_prefix="/help")

    @app.route("/", methods=["GET"])
    def index() -> str:
        """Display a landing page explaining login requirements."""
        return render_template("index.html")

    @app.route("/map", methods=["POST"])
    def map_view():
        origin_zip = (request.form.get("origin_zip") or "").strip()
        dest_zip = (request.form.get("destination_zip") or "").strip()
        html = build_map_html(origin_zip, dest_zip)
        if html is None:
            flash("Could not locate one or both ZIP codes.", "warning")
            return redirect(url_for("index"))
        return render_template("map.html", map_html=Markup(html))

    @app.route("/send", methods=["POST"])
    @login_required
    def send_email_route() -> ResponseReturnValue:
        """Send a quote summary email on behalf of an authenticated user.

        Inputs:
            origin_zip: ZIP code for the quote origin provided via form data.
            destination_zip: ZIP code for the quote destination provided via form data.
            email: Recipient email address submitted in the POST body.

        Returns:
            A redirect response back to :func:`quotes.new_quote` or
            :func:`index`, depending on validation outcomes.

        External dependencies:
            * :func:`services.mail.user_has_mail_privileges` to restrict usage
              to Freight Services staff accounts.
            * :func:`send_email` for the actual SMTP dispatch.
        """
        origin_zip = (request.form.get("origin_zip") or "").strip()
        dest_zip = (request.form.get("destination_zip") or "").strip()
        email = (request.form.get("email") or "").strip()

        if not user_has_mail_privileges(current_user):
            flash(
                "Quote emails are limited to Freight Services staff accounts.",
                "warning",
            )
            return redirect(url_for("quotes.new_quote"))

        if not email:
            flash("Recipient email is required to send a quote.", "warning")
            return redirect(url_for("index"))

        miles = get_distance_miles(origin_zip, dest_zip)
        miles_text = f"{miles:,.2f} miles" if miles is not None else "N/A"

        subject = f"Quote for {origin_zip} \u2192 {dest_zip}"
        body = (
            "Quote Details\n\n"
            f"Origin ZIP: {origin_zip}\n"
            f"Destination ZIP: {dest_zip}\n"
            f"Estimated Distance: {miles_text}\n"
            f"Generated: {datetime.utcnow().isoformat()}Z\n"
        )

        try:
            send_email(
                email,
                subject,
                body,
                feature="quote_email",
                user=current_user,
            )
            flash("Quote email sent.", "success")
        except MailRateLimitError as exc:
            flash(str(exc), "warning")
        except Exception as e:
            current_app.logger.exception("Email send failed: %s", e)
            flash("Failed to send email. Check SMTP settings.", "danger")

        return redirect(url_for("index"))

    return app
