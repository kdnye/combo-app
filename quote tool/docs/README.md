# Quote Tool Documentation Hub

This guide unifies the project documentation and inline comments so new contributors,
operators, and support staff can find authoritative references quickly. It links the
high-level documents—[`README.md`](../README.md), [`ARCHITECTURE.md`](../ARCHITECTURE.md),
and [`DEPLOYMENT.md`](../DEPLOYMENT.md)—with the in-app help center and the annotated
source files that explain key workflows.

## Documentation map

| Audience | Start here | Purpose |
| --- | --- | --- |
| Developers & reviewers | [`README.md`](../README.md) | Feature overview, quick-start environment setup, and development tips. |
| Architects | [`ARCHITECTURE.md`](../ARCHITECTURE.md) | Component breakdown and reimplementation guidance for other stacks. |
| Operations & SRE | [`DEPLOYMENT.md`](../DEPLOYMENT.md) | Production roll-out, environment variables, TLS, and maintenance runbooks. |
| Analysts & trainers | [`docs/README.md`](./README.md) *(this file)* | Cross-links every reference and summarizes the business logic. |
| End users | In-app Help Center (`/help`) | Task-focused guides rendered from templates in [`templates/help/`](../templates/help/). |

### Additional quick links

- [`flask_app.py`](../flask_app.py) & [`standalone_flask_app.py`](../standalone_flask_app.py) – entry points for the web server
  and API-only mode.
- [`docker-compose.yml`](../docker-compose.yml) & [`Dockerfile`](../Dockerfile) – container definitions referenced by
  the deployment guide.
- [`backups.md`](./backups.md) – Duplicati job automation, retention policy
  guidance, and monitoring notes.
- [`tests/`](../tests) – pytest suite exercised in local development and CI.
- [`user_seeding_runbook.md`](./user_seeding_runbook.md) – administrator checklist for preparing the CSV and loading
  accounts with the seeding script.

## Application overview

The Quote Tool exposes HTML and JSON experiences for generating Hotshot and Air freight
quotes. The application factory in [`app/__init__.py`](../app/__init__.py) wires together
Flask, SQLAlchemy, CSRF protection, global rate limiting, and the custom FSI theme before
registering the authentication, quote, admin, and help blueprints. Staff-only features such
as booking emails and the quote history dashboard rely on
[`services.mail.user_has_mail_privileges`](../services/mail.py) to ensure only approved
Freight Services accounts can access them. The helper `ensure_database_schema` invoked from
the factory automatically provisions BigQuery or SQL schemas and verifies that essential
templates such as `index.html`, `map.html`, and `new_quote.html` exist before serving
requests.

### Feature status and constraints

| Feature | Status | Notes |
| --- | --- | --- |
| Hotshot and Air quoting | ✅ Stable | Form and JSON paths persist quotes and metadata. |
| Booking email workflow (`/quotes/<id>/email`) | 🔒 Staff-only | Requires mail privileges; customers see the option disabled in the UI. |
| Volume-pricing email workflow (`/quotes/<id>/email-volume`) | 🔒 Staff-only | Offered when a quote trips configured thresholds. Uses the same privilege checks as booking emails. |
| Quote summary emailer (`/send`) | 🔒 Staff-only | Accessible from quote results and the admin quote listing when SMTP is configured. |
| Admin quote history (`/admin/quotes`) | ✅ Stable | Restricted to approved employees; includes CSV export and links to booking helpers. |
| Redis caching profile | ⚙️ Optional | Disabled unless `COMPOSE_PROFILES=cache` or `CACHE_TYPE` enable it. |
| Duplicati backups profile | ⚙️ Optional | Disabled unless the `backup` Compose profile is started. |
| BigQuery backend | 🧪 Optional | Supported through `BIGQUERY_*` variables but production defaults to PostgreSQL. |

Persistent data lives in [`app/models.py`](../app/models.py) where SQLAlchemy defines
users, quotes, password reset tokens, accessorials, and the rate tables used by the pricing
engine. JSON-formatted quote metadata keeps track of the accessorial breakdown, computed
miles, and warnings surfaced to the UI.

## Blueprint reference

### Authentication (`app/auth.py`)

- **Login (`/login`)** – Validates credentials and enforces configurable rate limits through
  helpers such as `_login_rate_limit_value()` and `_login_rate_limit_key()` that combine the
  caller IP address with the submitted email before delegating to
  [`flask-limiter`](https://flask-limiter.readthedocs.io/).
- **Registration (`/register`)** – Collects profile, company, and human-verification details.
  Emails ending in `@freightservices.net` become employee accounts that require manual
  approval, and successful registrations log an info message for admins.
- **Password reset (`/reset` and `/reset/<token>`)** – Generates signed reset links via
  `services.auth_utils.create_reset_token`, enforces throttling with `_reset_rate_limit_*`
  helpers, and verifies token expiry before calling
  `services.auth_utils.reset_password_with_token`.
- **Logout (`/logout`)** – Clears the active session with `flask_login.logout_user`.

### Quote workflow (`app/quotes/routes.py`)

- **New quote (`/quotes/new`)** – Accepts form and JSON submissions, converts dimensional
  inputs into billable weight, and selects Hotshot or Air pricing paths. Hotshot quotes
  delegate to `quote.logic_hotshot.calculate_hotshot_quote`, while Air quotes call
  `quote.logic_air.calculate_air_quote` after confirming the required rate tables exist.
  Threshold checks from `quote.thresholds.check_thresholds` warn when shipments exceed
  configured caps, and guarantee accessorials automatically add 25% of the linehaul when
  selected.
- **Email request (`/quotes/<quote_id>/email`)** – Prepares the booking details form and
  calculates convenience fees for staff with email privileges. Accessorials stored in the
  quote metadata feed the summary presented to users.
- **Volume email request (`/quotes/<quote_id>/email-volume`)** – Mirrors the booking flow
  but waives the admin fee so staff can escalate overweight/overvalue shipments for manual
  pricing assistance.

### Administration (`app/admin.py` & `quote/admin_view.py`)

- CSV-backed forms (`AccessorialForm`, `HotshotRateForm`, `ZipZoneForm`, etc.) keep the rate
  tables synchronized with the import/export utilities.
- `_sync_admin_role` aligns the `role` and `employee_approved` flags so admin toggles stay in
  sync with the UI.
- The blueprint uses decorators from [`app/policies.py`](../app/policies.py) to restrict
  access to employee and super-admin audiences.
- [`quote/admin_view.py`](../quote/admin_view.py) exposes `/admin/quotes` and
  `/admin/quotes.csv`, letting approved employees audit quote history, export sanitized CSV
  data, and jump into the staff-only email helpers.

### Help center (`app/help.py`)

- Routes under `/help` render contextual guides stored in [`templates/help/`](../templates/help/).
  The `HELP_TOPICS` list drives the sidebar in `help/index.html`, while dedicated endpoints
  serve long-form articles such as `quote_types`, `admin`, `password_reset`, and `register`.
- `_render_help_page` centralizes the logic that highlights the active topic and injects the
  structured summary data into the template.

## Pricing engine

- **Hotshot logic** – `quote.logic_hotshot.calculate_hotshot_quote` requests mileage from
  `quote.distance.get_distance_miles`, resolves the active zone with
  `services.hotshot_rates.get_hotshot_zone_by_miles`, and applies per-pound or per-mile
  charges with fuel surcharges based on the fetched `HotshotRate`. Zone "X" enforces a
  special $5.10/lb rate with a mileage-derived minimum charge.
- **Air logic** – `quote.logic_air.calculate_air_quote` stitches together ZIP-to-zone lookups,
  cost zone concatenations, and beyond charges. It retries reversed zone pairs before failing,
  computes the base charge using minimums and per-pound rates, and adds origin/destination
  beyond fees through `get_beyond_rate`.
- **Thresholds & warnings** – `quote.thresholds.check_thresholds` evaluates weight and price
  caps so the UI can surface warnings when quotes exceed tool limits defined in
  configuration.

## Data and rate management

- [`scripts/import_air_rates.py`](../scripts/import_air_rates.py) and
  [`scripts/seed_users.py`](../scripts/seed_users.py) transform CSV data into database rows.
  The admin dashboard reuses the same parsing helpers (for example, `save_unique`) to ensure
  consistent deduplication rules across manual and automated imports.
- [`init_db.py`](../init_db.py) initializes the schema, loads bundled rate tables, and
  optionally seeds an administrator using `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment
  variables.
- [`migrate_quotes.py`](../migrate_quotes.py) demonstrates how to move historical quotes
  between databases while preserving metadata.

## Email and notifications

- `app.__init__.send_email` wraps SMTP dispatch with sender-domain validation,
  per-recipient/user rate limiting via `services.mail.enforce_mail_rate_limit`, and audit
  logging through `services.mail.log_email_dispatch`. Configuration keys (`MAIL_SERVER`,
  `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, etc.) follow
  the conventions documented in `README.md` and `DEPLOYMENT.md`.
- `services.settings.load_mail_settings` and the **Admin → Settings** page allow
  super administrators to override configuration values such as SMTP credentials or rate
  limits at runtime without redeploying environment variables. Passwords are stored as
  `AppSetting` records flagged as secret so the UI never redisplays them.
- Quote summary emails initiated from `/send` include distance calculations from
  `quote.distance.get_distance_miles` alongside origin/destination metadata.

## Security, throttling, and policies

- Global rate limits are configured through environment variables such as
  `RATELIMIT_DEFAULT`, while authentication endpoints honour dedicated settings like
  `AUTH_LOGIN_RATE_LIMIT`, `AUTH_RESET_RATE_LIMIT`, and `AUTH_REGISTER_RATE_LIMIT`.
- The registration form enforces a math-based human verification challenge generated by
  `_issue_registration_challenge`, and employee registrations default to `employee_approved=False`
  until an administrator reviews them.
- Email functionality is limited to staff accounts through `services.mail.user_has_mail_privileges`,
  preventing customer accounts from dispatching quotes via SMTP.

## Deployment and operations

- Follow [`README.md`](../README.md#quick-start) for local setup, rate imports, and Docker-based
  workflows, then graduate to the step-by-step production checklist in
  [`DEPLOYMENT.md`](../DEPLOYMENT.md).
- TLS assets and reverse proxy configuration live in `deploy/swag/`. Certificates issued by SWAG
  are written under `deploy/swag/etc/letsencrypt/`, and the proxy template in
  `deploy/swag/proxy-confs/quote_tool.subdomain.conf` forwards traffic to the Flask app.
- Database migrations run with `alembic upgrade head` inside the container or host environment.

## Testing and quality assurance

- Execute `pytest` from the repository root after configuring environment variables to ensure
  authentication, quoting, and import workflows continue to pass.
- The `tests/` package covers pricing calculations, admin utilities, and API behaviour; extend
  it alongside feature work to keep coverage meaningful.

## Help center quick reference

| Endpoint | Template | Highlights |
| --- | --- | --- |
| `/help` | `templates/help/index.html` | Sidebar-driven overview with quick links to getting started, quoting, booking, and account topics. |
| `/help/quoting` | `templates/help/index.html` (topic focus) | Step-by-step quoting reminders with links to the quote-type deep dive. |
| `/help/quote-types` | `templates/help/quote_types.html` | Compares Hotshot and Air profiles, pros/cons, and when to choose each option. |
| `/help/admin` | `templates/help/admin.html` | Administrator runbook for rate tables, accessorials, and approval workflows. |
| `/help/password-reset` | `templates/help/password_reset.html` | Walkthrough of the request and token-based reset flow backed by `app.auth`. |
| `/help/register` | `templates/help/register.html` | Detailed registration checklist covering required fields and follow-up emails. |

## Inline documentation index

Use these annotated modules when you need deeper implementation notes:

- [`app/__init__.py`](../app/__init__.py) – factory setup, Google Maps embedding, SMTP helper,
  and setup verification that ensures database tables and templates exist.
- [`app/auth.py`](../app/auth.py) – route-level docstrings explaining required fields,
  validation flows, and special employee-handling logic.
- [`app/quotes/routes.py`](../app/quotes/routes.py) – end-to-end quote processing, metadata
  persistence, and warning generation.
- [`app/admin.py`](../app/admin.py) – dataclasses describing CSV schemas, form validation
  rules, and role synchronization helpers.
- [`app/help.py`](../app/help.py) – structured topic metadata driving the help center and
  route docstrings mapping to templates.
- [`quote/logic_hotshot.py`](../quote/logic_hotshot.py) & [`quote/logic_air.py`](../quote/logic_air.py) –
  pricing formulas and defensive fallbacks for missing rate data.
- [`services/`](../services) – shared business logic (`auth_utils`, `hotshot_rates`, `mail`, `quote`) with
  docstrings that connect database queries to user-facing behaviour.

Keeping this map close at hand ensures code comments and user-facing docs stay aligned as the
Quote Tool evolves.
