# Deployment Guide

This document describes how to promote the Quote Tool application into a
production-like environment using Docker Compose and the bundled SWAG (Secure
Web Application Gateway) reverse proxy. It expands on the quick-start notes in `README.md` and is intended for
operations staff who need precise, repeatable steps to stand up the service. For
a cross-reference of the full documentation set, consult [docs/README.md](docs/README.md).

## 1. Prerequisites

1. **Host operating system** – Linux distribution with long-term support (Ubuntu
   22.04 LTS or similar). The instructions assume root or sudo access.
2. **Container runtime** – Docker Engine 24+ and Docker Compose v2. If your
   platform ships Compose as a plugin, ensure `docker compose version` succeeds.
3. **Domain name and DNS** – Create records for the hostname you will publish.
   SWAG uses the `URL` and `SUBDOMAINS` environment variables to build the
   certificate request (for example, `URL=example.com` and `SUBDOMAINS=quote`
   expects `quote.example.com`). Point the resulting record at the Docker host.
4. **Certificate strategy** – Decide how SWAG should satisfy the Let’s Encrypt
   challenge before you boot the container. HTTP validation requires ports
   80/443 reachable from the internet; DNS validation needs API credentials for
   the provider you set in `DNSPLUGIN`. You can also import certificates issued
   by a corporate PKI by copying them into `deploy/swag/etc/letsencrypt/live/`.
5. **External services** – Provision the dependencies used by the Quote Tool:
   - **Database** – PostgreSQL 13+ is recommended for production. SQLite works
     for local development but is not suited for multi-user deployments.
   - **Google Maps API access** – Enable the Distance Matrix API and obtain an
     API key.
   - **Redis (optional)** – Required only when `CACHE_TYPE` is set to a Redis
     backend (e.g., `redis`).
   - **SMTP relay (optional)** – Needed for password reset emails. Configure the
     `MAIL_*` settings if you enable this feature.

## 2. Fetch the application

Clone the repository (or download the release archive) onto the deployment
host:

```bash
sudo mkdir -p /opt/quote_tool
sudo chown "$USER" /opt/quote_tool
cd /opt/quote_tool
git clone https://example.com/your-fork.git .
```

If you maintain a private fork, update the URL accordingly. Verify the working
tree is clean before continuing:

```bash
git status -sb
```

## 3. Configure environment variables

Create a `.env` file alongside `docker-compose.yml`. The Compose project reads
these values and passes them into the containers. Generate a deployment secret
with `python -c 'import secrets; print(secrets.token_urlsafe(32))'` and paste
the output into `SECRET_KEY` so the Flask app can reuse it across restarts. The
LinuxServer PostgreSQL container expects a host UID/GID via `PUID` and `PGID`,
and the application defaults to that bundled database whenever
`POSTGRES_PASSWORD` is present. Helper scripts executed on the host machine read
`POSTGRES_HOST` (defaulting to `postgres`) so set it to the reachable hostname
when connecting to an external database without overriding `DATABASE_URL`.
For example:

- macOS/Linux: `POSTGRES_HOST=localhost python init_db.py`
- PowerShell: `$env:POSTGRES_HOST="localhost"; python init_db.py`
- Command Prompt: `set POSTGRES_HOST=localhost && python init_db.py`

Each variant keeps the override scoped to the current shell session so the
Compose deployment can continue using the container hostname.
Override `DATABASE_URL` only when pointing the app at a fully custom connection
string.

```dotenv
# Core application settings
# Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
SECRET_KEY=replace-with-long-random-string
GOOGLE_MAPS_API_KEY=your-google-key
FLASK_DEBUG=false
TZ=UTC
PUID=1000
PGID=1000
POSTGRES_USER=quote_tool
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=quote_tool
POSTGRES_HOST=postgres
DUPLICATI_WEBSERVICE_PASSWORD=generate-a-long-ui-password
# Reverse proxy configuration (required when running SWAG)
URL=example.com
SUBDOMAINS=quote
VALIDATION=http
EMAIL=ops@example.com
# DNSPLUGIN=cloudflare  # Required for DNS validation, remove when using http validation
# DATABASE_URL=postgresql+psycopg2://override_user:override_password@override-host:5432/override_db

# Optional Docker Compose profiles (comma-separated)
# COMPOSE_PROFILES=cache,backup  # Start Redis caching and the Duplicati backup agent

# Optional tuning (uncomment as needed)
# DB_POOL_SIZE=10
# CACHE_TYPE=redis
# CACHE_REDIS_URL=redis://redis-host:6379/0
# RATELIMIT_STORAGE_URI=redis://redis-host:6379/1
# MAIL_DEFAULT_SENDER=quote@freightservices.net
# MAIL_SERVER=smtp.office365.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=quote@freightservices.net
# MAIL_PASSWORD=app-password
# MAIL_ALLOWED_SENDER_DOMAIN=freightservices.net
# MAIL_PRIVILEGED_DOMAIN=freightservices.net
# MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY=25
# MAIL_RATE_LIMIT_PER_USER_PER_HOUR=10
# MAIL_RATE_LIMIT_PER_USER_PER_DAY=50
# MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR=200
# RATE_DATA_DIR=/app/rates  # Custom directory for CSV imports
# ADMIN_EMAIL=admin@example.com
# ADMIN_PASSWORD=initial-password
```

### Variable reference

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Secures Flask sessions and CSRF tokens. Generate at least 32 random bytes (see `python -c 'import secrets; print(secrets.token_urlsafe(32))'`). |
| `FLASK_DEBUG` | Yes | Set to `false` in production to disable Flask's interactive debugger and reloader. |
| `GOOGLE_MAPS_API_KEY` | Yes | Authenticates calls to Google’s Distance Matrix API. |
| `TZ` | Yes | Time zone passed to the PostgreSQL container. Determines backup timestamps and log rotation. |
| `PUID`, `PGID` | Yes | Map the PostgreSQL container's user and group IDs to a host account that owns `./data/postgres`. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Yes | Credentials and database name consumed by the LinuxServer PostgreSQL container and the Flask app's default connection string. |
| `POSTGRES_HOST` | No | Hostname for helper scripts and local tooling that connect outside Docker. Defaults to `postgres` to target the bundled container. |
| `URL`, `SUBDOMAINS` | Yes | Domain pieces passed to SWAG and Certbot. For example, `URL=example.com` with `SUBDOMAINS=quote` issues a certificate for `quote.example.com`. |
| `VALIDATION` | Yes | Determines how SWAG proves domain ownership. Set to `http` to open ports 80/443 or `dns` when supplying a DNS plugin. |
| `EMAIL` | Yes | Administrative email address presented to Let’s Encrypt for expiration notices. |
| `DNSPLUGIN` | Conditional | Required when `VALIDATION=dns`. Matches the plugin name documented by SWAG (for example `cloudflare`). |
| `DATABASE_URL` | No | Override the default connection string if you are using an external database. Leave unset to target the Compose-managed PostgreSQL instance at `postgres:5432`. |
| `DB_POOL_SIZE` | No | Overrides the SQLAlchemy connection pool size when using PostgreSQL or MySQL. |
| `COMPOSE_PROFILES` | No | Enable optional Compose services, e.g., set `COMPOSE_PROFILES=cache` to start the bundled Redis container. |
| `CACHE_TYPE` / `CACHE_REDIS_URL` | No | Configure Flask-Caching. Leave unset to disable caching or rely on the defaults applied when the `cache` profile is active (`redis` / `redis://redis:6379/0`). |
| `RATELIMIT_STORAGE_URI` | No | Storage backend for Flask-Limiter counters. Defaults to `memory://` unless the `cache` profile is enabled, in which case it becomes `redis://redis:6379/1`. |
| `MAIL_*` | No | Configure outbound email (SMTP host, credentials, TLS/SSL flags). Needed for password resets. Super admins can also supply these values through the **Admin → Mail Settings** page at runtime. |
| `MAIL_ALLOWED_SENDER_DOMAIN` | No | Restricts `MAIL_DEFAULT_SENDER` to the Office 365 tenant domain (defaults to `freightservices.net`). |
| `MAIL_PRIVILEGED_DOMAIN` | No | Controls which user email domains can access advanced mail features. |
| `MAIL_RATE_LIMIT_PER_*` | No | Tune per-user, per-feature, and per-recipient rate limits for outbound email traffic. |
| `RATE_DATA_DIR` | No | Directory containing the rate CSV files consumed by `init_db.py`. Defaults to the repository root. |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | No | When set, `init_db.py` bootstraps an administrator account with these credentials. |

Never commit the `.env` file to version control. Restrict filesystem
permissions (`chmod 600 .env`) so only the deployment user can read it.

### Optional services and feature gating

- **SMTP-dependent workflows** – Booking and volume-pricing email helpers, along with the quote summary emailer, require
  outbound email credentials. Without `MAIL_*` values or runtime overrides, those buttons remain disabled for all users.
- **Staff-only email features** – Even with SMTP enabled, only users whose email domain matches `MAIL_PRIVILEGED_DOMAIN` and who
  are approved employees or super admins can access the booking and volume email forms. Customer accounts will see the controls
  in a disabled state.
- **Redis caching** – Disabled unless you start the `cache` profile or explicitly set `CACHE_TYPE`. Confirm Redis credentials are
  reachable before enabling it.
- **Duplicati backups** – Disabled unless the `backup` profile is enabled. Start the container when you are ready to manage backup
  jobs.
- **BigQuery backend** – Supported through `BIGQUERY_*` environment variables but PostgreSQL remains the default for production
  releases.

## 4. Prepare the database

The Compose stack ships with LinuxServer's PostgreSQL container, which stores
its cluster beneath `/config` (mapped to `./data/postgres` on the host).

1. Create the host data directories and grant ownership to the user referenced by
   `PUID`/`PGID`:

   ```bash
   sudo mkdir -p /opt/quote_tool/data/postgres /opt/quote_tool/data/duplicati
   sudo chown "${PUID:-1000}:${PGID:-1000}" /opt/quote_tool/data/postgres /opt/quote_tool/data/duplicati
   ```

   Replace `1000` with the UID/GID that should own the files. Matching the IDs
   prevents LinuxServer's init scripts from failing their permission checks and
   ensures Duplicati can persist job definitions under `/config`.

2. Start the PostgreSQL container and wait for the health check to report
   `healthy`:

   ```bash
   docker compose up -d postgres
   docker compose ps postgres
   ```

   The service listens on the internal Docker network at `postgres:5432`; the
   Flask app and helper scripts automatically target this host when
   `POSTGRES_PASSWORD` is set.

3. If you prefer a managed database service instead of the bundled container,
   set `DATABASE_URL` in `.env` and skip step 2. Confirm the deployment host can
   reach the managed instance over TCP port 5432 (or your custom port) before
   continuing.

## 5. Build and start the containers

From the project root:

```bash
docker compose pull  # Fetch updated base images
docker compose build --no-cache  # Optional: force a clean build after upgrades
```

Start the application stack in the background once PostgreSQL reports
`healthy`:

```bash
docker compose up -d quote_tool swag
docker compose --profile backup up -d duplicati
```

The `quote_tool` container starts Gunicorn listening on port 5000 while NGINX
terminates TLS and proxies traffic. Duplicati starts in the optional `backup`
profile; omit the second command when you do not want the backup service
running on the host. Inspect the logs to ensure startup completes successfully:

```bash
docker compose logs -f quote_tool
```

### Apply database migrations

Run Alembic migrations inside the container to create/upgrade tables:

```bash
docker compose run --rm quote_tool alembic upgrade head
```

You can rerun this command after future deployments to apply schema updates.

### Enable Redis caching and shared rate limiting (optional)

Redis support is packaged as a Compose profile so operations teams can opt in on
a per-environment basis. To enable it:

1. Define `COMPOSE_PROFILES=cache` in `.env` (or export it in your shell before
   running `docker compose`). The profile hooks into
   [`config.Config`](config.py) so the application automatically falls back to
   `redis://redis:6379/0` for caching and `redis://redis:6379/1` for
   Flask-Limiter counters.
2. Override `CACHE_TYPE`, `CACHE_REDIS_URL`, or `RATELIMIT_STORAGE_URI` only if
   you are targeting an external Redis deployment. Otherwise the defaults above
   will match the bundled container.
3. Prepare persistent storage and permissions:

   ```bash
   sudo mkdir -p /opt/quote_tool/data/redis
   sudo chown "${PUID:-1000}:${PGID:-1000}" /opt/quote_tool/data/redis
   ```

4. Start Redis alongside the existing services and verify the health check:

   ```bash
   docker compose --profile cache up -d redis
   docker compose exec redis redis-cli PING
   ```

   The second command should print `PONG` once the server is ready.

5. **Rate-limit storage migration:** Switching from the default in-memory
   backend to Redis requires a clean slate so stale counters do not block
   legitimate users. After enabling the profile, flush Redis database `1`
   (reserved for Flask-Limiter) and restart Gunicorn to load the new
   configuration:

   ```bash
   docker compose exec redis redis-cli -n 1 FLUSHDB
   docker compose restart quote_tool
   ```

   Flushing database `1` leaves the cache in database `0` untouched while
   ensuring Gunicorn workers start tracking limits in the shared store.

### Seed rate tables and admin user

The `init_db.py` helper imports base rate data and optionally creates an initial
administrator. Run it once after migrations finish:

```bash
docker compose run --rm quote_tool python init_db.py
```

If `RATE_DATA_DIR` is defined, the script reads CSV files from that directory.
Otherwise it falls back to the CSVs checked into the repository root. Provide
`ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` (or export them temporarily) to
bootstrap the first admin account.

## 6. Maintenance

### Backups

The Compose stack ships with LinuxServer's [Duplicati](https://www.duplicati.com/)
container to back up databases and rate assets alongside traditional `pg_dump`
exports. Duplicati persists its configuration under `./data/duplicati`, so the
service resumes scheduled jobs after restarts.

#### Duplicati initial configuration

1. **Reach the web UI.** The container listens on port 8200 bound to
   `127.0.0.1`. On the Docker host, open `https://127.0.0.1:8200` in a browser
   and accept the self-signed certificate. When administering from another
   workstation, create an SSH tunnel first:

   ```bash
   ssh -L 8200:127.0.0.1:8200 ops@example-host
   ```

   Sign in with the password stored in `DUPLICATI_WEBSERVICE_PASSWORD` and
   record it in your password vault. The UI does not require a username.

2. **Create a backup job.** Click *Add backup → Configure a new backup* and
   supply:

   - **General** – Friendly name (for example, "Quote Tool production"),
     optional description, and *Encryption* set to **AES-256**. Enter a unique
     passphrase and save it in a secret manager; Duplicati cannot restore
     encrypted sets without it.
   - **Destination** – Choose the storage type that matches your target (Amazon
     S3, Azure Blob Storage, SMB share, etc.) and provide credentials with
     least-privilege access. Use the *Test connection* button before saving.
   - **Source data** – Expand `/source` and select the directories exported from
     the Compose stack:
       - `/source/postgres` (PostgreSQL cluster)
       - `/source/redis` (Redis append-only file, when the cache profile is active)
       - `/source/instance/app.db` (SQLite database used by helper scripts)
       - `/source/rates` (CSV rate inputs mounted from the repository)

     Switch to *Edit as text* under **Filters** and replace the defaults with:

     ```
     + /source/postgres/**
     + /source/redis/**
     + /source/instance/app.db
     + /source/rates/*.csv
     - *
     ```

     The catch-all exclude prevents accidental inclusion of the entire
     repository while guaranteeing the filtered paths stay protected.
   - **Schedule** – Run the job daily during a maintenance window (e.g., 02:00
     server time) and enable email or webhook notifications if your backup
     destination supports them.
   - **Options** – Enable *Smart backup retention* and keep at least 7 daily, 4
     weekly, and 12 monthly versions to balance rollback flexibility with
     storage consumption.

   Save the job and trigger *Run now* to generate the initial backup set.

3. **Firewall and monitoring.** The UI is only exposed on the loopback interface
   but still honour host-based firewalls or security groups so port 8200 remains
   inaccessible from untrusted networks. Observe the health check and logs with:

   ```bash
   docker compose ps duplicati
   docker compose logs -f duplicati
   ```

   Job-level logs live under `data/duplicati/logs/`, and successful runs update
   `data/duplicati/duplicati-server.sqlite`. Consider forwarding container logs
   to your central monitoring stack so backup failures page the on-call team.

#### Manual database dumps (fallback)

Continue exporting PostgreSQL snapshots before major upgrades or schema changes
in case you need a clean SQL dump for point-in-time recovery:

```bash
docker compose exec postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > data/postgres/backups/"$(date +%Y%m%d-%H%M)-quote_tool.sql"
```

The command writes a consistent snapshot that can be restored with `psql` or
`pg_restore`. Retain multiple generations so you can roll back if a migration or
bad import slips through testing. Consult [`docs/backups.md`](docs/backups.md)
for automation tips and job export examples.

### Upgrades

1. Back up the database using the command above (or your enterprise backup
   solution).
2. Pull updated images:

   ```bash
   docker compose pull postgres quote_tool swag
   ```

3. Recreate the containers:

   ```bash
   docker compose up -d postgres
   docker compose up -d quote_tool swag
   ```

   Wait for `postgres` to return to the `healthy` state, then restart the
   application containers. Apply database migrations after each upgrade with
   `docker compose run --rm quote_tool alembic upgrade head`.

Review LinuxServer's release notes for breaking changes, especially when the
underlying PostgreSQL major version bumps. Major upgrades may require running
`pg_upgrade` manually or restoring from dump files.

## 7. Configure the reverse proxy and TLS

The Compose stack includes LinuxServer's SWAG container to terminate HTTPS and
proxy traffic to `quote_tool`. Certbot runs automatically inside SWAG; prepare
the environment before launching the service:

1. Populate `URL`, `SUBDOMAINS`, `VALIDATION`, and `EMAIL` in `.env`. Add
   `DNSPLUGIN` and the provider-specific credentials when using DNS challenges
   (for example, `CLOUDFLARE_DNS_API_TOKEN` for Cloudflare).
2. Choose a validation strategy:
   - **HTTP validation** – Set `VALIDATION=http`, forward ports 80/443 through
     your firewall, and ensure the DNS record points at the host. Start SWAG
     with `docker compose up -d swag` and monitor progress via
     `docker compose logs -f swag`.
   - **DNS validation** – Set `VALIDATION=dns`, define `DNSPLUGIN`, and provide
     the plugin's API credentials in `.env`. SWAG updates the DNS records on
     your behalf when it runs `certbot`.
3. Review and adjust `deploy/swag/proxy-confs/quote_tool.subdomain.conf`. The
   template already routes traffic to `quote_tool:5000` and exposes optional
   Authelia includes—uncomment them once an Authelia container is on the same
   network. Restart the proxy after changes:

   ```bash
   docker compose restart swag
   ```

Certificate material is stored under `deploy/swag/etc/letsencrypt/` and Nginx
logs are available in `deploy/swag/log/nginx/`. SWAG renews certificates
automatically, but you can trigger or test renewals manually:

```bash
docker compose exec swag certbot renew --dry-run
docker compose exec swag certbot renew
docker compose restart swag  # Reload configuration after manual changes
```

## 7. Health checks and smoke tests

After the proxy is running, perform a quick validation:

```bash
curl -Ik https://quotes.example.com/
```

A successful response returns `HTTP/1.1 200 OK` (or a redirect to `/login`).
Log in with the administrator credentials created earlier and verify you can
request a quote.

## 8. Routine maintenance

- **Deploying updates** – Pull the latest code, rebuild images, run migrations,
  and restart the stack:

  ```bash
  git pull
  docker compose build
  docker compose up -d quote_tool swag
  docker compose run --rm quote_tool alembic upgrade head
  ```

- **Backups** – Keep Duplicati jobs enabled and monitor their schedules, then
  archive manual PostgreSQL dumps and the `.env` file alongside the SWAG
  configuration under `deploy/swag/` (proxy templates, logs, and certificates).
  The application is stateless outside of these assets.
- **Monitoring** – Forward container logs to your logging platform (e.g.,
  `docker compose logs -f` piped into `fluent-bit`) and consider probing the
  `/healthz` endpoint if you expose one via a future update.

## 9. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `sqlalchemy.exc.OperationalError` on startup | Confirm the database host, port, and credentials in `DATABASE_URL`. Ensure outbound firewall rules permit traffic to the DB. |
| HTTP 502 from SWAG | Check `docker compose logs swag` for certificate or upstream errors. Verify the `quote_tool` container is healthy and listening on port 5000. |
| Let’s Encrypt challenge fails | Review `docker compose logs swag` for `certbot` output. Confirm `URL`/`SUBDOMAINS` match the DNS record and that the selected validation method (HTTP vs. DNS) is reachable. |
| Distance calculations fail | Validate `GOOGLE_MAPS_API_KEY` has the Distance Matrix API enabled and the server’s IP is authorized. |
| Password reset emails do not send | Set the `MAIL_*` environment variables and confirm the SMTP relay allows connections from the Docker host. |

## 10. Security considerations

- Rotate the `SECRET_KEY` and database credentials if you suspect compromise.
  Changing `SECRET_KEY` will invalidate active sessions.
- Restrict SSH and Docker API access to trusted administrators. Use a firewall
  or security groups to allow inbound traffic only on ports 80/443 (and the
  database port if required).
- Keep Docker Engine, the base images, and the host OS patched. Rebuild the
  image after applying dependency updates in `requirements.txt`.

Following this runbook yields a reproducible deployment of Quote Tool with HTTPS
termination, seeded data, and a hardened configuration ready for production.
