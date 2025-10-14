# combo-app

Unified home for the three Freight Services Inc. internal tools that previously lived in separate repositories. The goal of thi
s monorepo is to make it easy to operate every app together while preserving their existing build and deployment workflows.

## Repository layout

```text
apps/
  expenses/        # Python/Flask expense report builder
  hana-inventory/  # Hana operating table inventory checker
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
| Hana Inventory | Google Apps Script that audits the "Mizuho Inventory" Google Sheet and emails weekly alerts when counts drift. | `apps/hana-inventory/app` |
| Hotshot Quote Tool | Flask application with Alembic migrations and utilities for calculating freight quotes. | `apps/quote-tool/flask_app.py` |

Visiting the Hana inventory Flask service root now presents a combined landing
page that links to each tool. The original inventory dashboard is available at
`/hana-inventory`.

Refer to each app's README for setup, testing, and deployment details:

- [`apps/expenses/README.md`](apps/expenses/README.md)
- [`apps/hana-inventory/APP_README.md`](apps/hana-inventory/APP_README.md)
- [`apps/quote-tool/README.md`](apps/quote-tool/README.md)

## Developer tooling

- **Docker Compose:** `docker compose -f infra/compose/dev.yml up --build` launches the expenses UI, quote tool API, supporting Postgres instance, and the Hana inventory dashboard together. Each service binds to a unique port so you can exercise cross-app workflows locally.
- **Continuous Integration:** GitHub Actions workflows lint and test each application when their subtrees change. See `.github/workflows/` for details on the Python version and commands executed per app.
- **Shared code:** Place reusable Python modules in `packages/` and import them from applications as needed.

## Contributing

Follow the branching, commit, and PR guidance in `agents.md`. When changing any application, update its documentation alongside
code changes and run the relevant test suites before committing.
