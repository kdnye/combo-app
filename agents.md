agents.md

Repository governance and developer runbook for the unified FSI internal app (Docker-first, monorepo).

Purpose

Standardize how we build, deploy, expose, and maintain multiple app modules as a single system that runs on an internal Docker host with optional public ingress.

Roles & ownership

Maintainer (Code): Reviews PRs, enforces style/tests.

Maintainer (Ops): Owns Docker/Compose, secrets, backups, monitoring.

Release Manager: Cuts versions/tags and promotes to prod.

Security Champion: Reviews dependencies, ingress rules, auth.

Document current people in OWNERS (one per area).

Branching & releases

Default branch: main (protected).

Feature work: feat/<area>-<short>; fixes: fix/<area>-<short>.

Release cadence: tag semantic versions vMAJOR.MINOR.PATCH.

Changelog: keep CHANGELOG.md with Keep a Changelog format.

Coding standards

Language-specific formatters/linters enforced via pre-commit hooks.

Python: black, ruff, typing for new/changed code; tests with pytest.

Node/TS (if present): eslint, prettier, tsc --noEmit.

API contracts: JSON Schema or OpenAPI; validate at CI.

Commit/PR

Small, focused commits. Conventional commits style recommended.

PR template: problem → change → risk → test evidence → rollout plan.

Include migration/backfill steps when DB/queues change.

Monorepo layout (example)
apps/
  web/            # UI or Flask/FastAPI app
  admin/
  worker/         # background jobs / Celery / RQ
packages/
  shared-lib/     # shared code
infra/
  docker/         # Dockerfiles, healthchecks
  compose/        # compose.*.yml overlays
  ingress/        # SWAG/Traefik/NGINX configs
scripts/          # init_db, data import, maintenance

Docker/Compose policy

Each app has its own Dockerfile and healthcheck.

Compose profiles: cache, backup, ingress, dev.

Images tagged from git SHA and semver; never latest in prod.

Volumes for stateful services (DB, Redis, instance data).

Configuration

All runtime config via environment variables. Document in README.

Secrets sourced from .env (not committed) or Docker secrets.

Ingress

Default: internal-only. Public exposure is opt-in per route.

Supported options (pick one per environment):

SWAG (linuxserver/swag) – Nginx + Let’s Encrypt.

Traefik – dynamic config + ACME.

NGINX Proxy Manager – UI-driven.

All public routes require HTTPS and auth (SSO where possible).

Database & migrations

Primary DB: Postgres (containerized). Local dev may use SQLite only for unit tests if needed.

Migrations via Alembic (Python) or Prisma/Knex (Node) depending on service.

scripts/init_db.py (or service-equivalent) must be idempotent.

Seeding: CSV/fixtures stored under data/ or scripts/.

Observability

Logging: JSON to stdout; structured fields: ts, level, svc, msg, trace_id.

Metrics: Prometheus endpoint /metrics (if feasible) or StatsD.

Health: /healthz (liveness) and /readyz (readiness) per service.

Backups & DR

DB backups via Duplicati or native snapshots on the host.

Retention: 7 daily, 4 weekly, 6 monthly. Test restore quarterly.

Store restores/DR steps in RUNBOOK.md.

Security

Minimal inbound ports; all admin UIs bound to localhost unless via VPN.

Fail2ban (optional) for Nginx/SWAG logs.

Dependencies scanned in CI (e.g., pip-audit, npm audit, trivy).

Keys/tokens rotate every 90 days.

Checklists

New service checklist



Release checklist



