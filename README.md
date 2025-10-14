# combo-app

Unified home for the three Freight Services Inc. internal tools that previously lived in separate repositories. The goal of thi
s monorepo is to make it easy to operate every app together while preserving their existing build and deployment workflows.

## Repository layout

```text
apps/
  expenses/        # Python/Flask expense report builder
  quote-tool/      # Hotshot freight quote management portal
infra/             # Shared Docker Compose bundles and ops assets
packages/          # Reusable Python packages
agents.md          # Governance and workflow guidance for the monorepo
```

Each application keeps its own Dockerfiles, documentation, and tests. When new shared code or infrastructure is introduced, add
 it under `packages/` or `infra/` following the guidance in `agents.md`.

## Working with the applications

| App | Description | Primary entry point |
| --- | ----------- | ------------------- |
| Expenses | Flask UI for assembling reimbursable expense reports and uploading receipts. | `apps/expenses/fsi_expenses_web/__init__.py` |
| Hotshot Quote Tool | Flask application with Alembic migrations and utilities for calculating freight quotes. | `apps/quote-tool/flask_app.py` |

Authenticated quote tool users land on `/workspace`, a dedicated operations hub
that highlights the quoting workflow and exposes quick links to the supporting
expense reporting application.

Refer to each app's README for setup, testing, and deployment details:

- [`apps/expenses/README.md`](apps/expenses/README.md)
- [`apps/quote-tool/README.md`](apps/quote-tool/README.md)

## Container image for unified landing page

Deployments that target the repository root can now build a single container
image using the top-level `Dockerfile`. The resulting image runs the quote tool
Flask application, which surfaces the new `/workspace` landing page alongside
the quoting features. Configure cross-application links at runtime with the
following environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `EXPENSES_APP_URL` | `http://localhost:8080/` | Location of the Expenses UI |

Set `PORT` (defaults to `8000`) if your hosting platform requires binding to a
specific port. The container uses Gunicorn as the process manager and stores its
SQLite database inside the writable application directory.

## Developer tooling

- **Docker Compose:** `docker compose up --build` now launches the Core Freight Services launcher (Next.js, port 3000), the expenses UI (Flask, port 8080), the quote tool API (Flask, port 5000), and the supporting Postgres instance. Each service binds to a unique port so you can exercise cross-app workflows locally while the launcher points at the containerised backends by default. The former `infra/compose/dev.yml` layout is still available if you need a Compose file scoped to the infrastructure assets.
- **Continuous Integration:** GitHub Actions workflows lint and test each application when their subtrees change. See `.github/workflows/` for details on the Python version and commands executed per app.
- **Shared code:** Place reusable Python modules in `packages/` and import them from applications as needed.

## Contributing

Follow the branching, commit, and PR guidance in `agents.md`. When changing any application, update its documentation alongside
code changes and run the relevant test suites before committing.
