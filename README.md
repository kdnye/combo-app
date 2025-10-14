README.md
# combo-app

Overview

This repo hosts multiple app modules consolidated into one Dockerized system that runs on an internal server. Specific HTTP routes can be optionally exposed to the public internet through a reverse proxy. Goal: one build, consistent ops, minimal toil.

Features

Monorepo with shared packages

Standard Docker/Compose stack (Postgres, Redis optional)

Pluggable ingress (SWAG/Traefik/NGINX Proxy Manager)

Scripted DB init/seed and backups

Architecture (logical)
[Users/Staff]───HTTPS──►[Ingress (SWAG/Traefik)]──►[apps:web,admin,api]
                                            │
                                            └──►[Static/Media]
[Jobs/Workers]──►[Redis]* ──► [apps:worker]
[All apps] ──► [Postgres]

*optional

Repo structure (simplified)

apps/ – services (web/api/admin/worker)

packages/ – shared libraries

infra/docker/ – Dockerfiles

infra/compose/ – compose files and overlays

infra/ingress/ – proxy configs (SWAG/Traefik/NPM)

scripts/ – init, migrations, imports, maintenance

Requirements

Docker Engine 24+

Docker Compose v2+

Optional: VS Code Dev Containers

Quick start (dev)

Copy .env.example → .env and fill required values.

Build & run:

docker compose -f infra/compose/compose.dev.yml up --build

App web UI at http://localhost:5000 (adjust port per service).

First-time DB setup
docker compose exec app python scripts/init_db.py --data-dir ./data
Environment variables

Create .env in repo root. Example keys:

Key	Description	Example
POSTGRES_PASSWORD	DB password	change-me
POSTGRES_DB	Database name	appdb
POSTGRES_USER	DB user	appuser
DATABASE_URL	SQLAlchemy/driver URL	postgresql+psycopg2://appuser:...
GOOGLE_MAPS_API_KEY	External API key (if used)	...
COMPOSE_PROFILES	Enable optional services	cache,backup,ingress

Add service-specific keys under each app’s README (or below).

Running with ingress (public routes)

Pick one provider and use the matching compose overlay:

SWAG: TLS via Let’s Encrypt, Nginx-based. Put vhost files in infra/ingress/swag/.

Traefik: Dynamic labels on services; ACME configured in infra/ingress/traefik/.

NGINX Proxy Manager: Point-and-click; not recommended for IaC.

Example:

docker compose \
  -f infra/compose/compose.dev.yml \
  -f infra/compose/compose.ingress.yml \
  --profile ingress up -d
Backups

Enable the backup profile to run Duplicati targeting DB volumes.

Test restores into a scratch DB monthly.

Development

Pre-commit hooks: pre-commit install.

Lint/test:

make check   # or: ruff/black/pytest

Dev container (VS Code): open folder, “Reopen in Container”.

Testing

Unit tests in each app under tests/.

Compose service test runs suite in CI:

docker compose run --rm test
Deployment (internal server)

Pull repository on the server.

Provide .env and TLS/ingress config.

docker compose -f infra/compose/compose.prod.yml up -d

Verify health endpoints: /healthz, /readyz.

Troubleshooting

Container restarts: docker compose logs -f <service>

DB connectivity: ensure POSTGRES_HOST is reachable (override to localhost when running helper scripts outside Docker).

Stuck migrations: run migration head and inspect Alembic table.

Roadmap

Office 365 SSO (OIDC) for all public/admin routes

Centralized metrics and log aggregation

Blue/green or canary releases via labels

License

Internal use only (FSI).
