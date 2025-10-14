# combo-app

Unified home for the three Freight Services Inc. internal tools that previously lived in separate repositories. The goal of thi
s monorepo is to make it easy to operate every app together while preserving their existing build and deployment workflows.

## Repository layout

```text
apps/
  expenses/        # Expense Report Builder SPA
  hana-inventory/  # Hana operating table inventory checker (Apps Script)
  quote-tool/      # Hotshot freight quote management portal
agents.md          # Governance and workflow guidance for the monorepo
```

Each application keeps its own Dockerfiles, documentation, and tests. When new shared code or infrastructure is introduced, add
 it under `packages/` or `infra/` following the guidance in `agents.md`.

## Working with the applications

| App | Description | Primary entry point |
| --- | ----------- | ------------------- |
| Expenses | Offline-capable web client for assembling reimbursable expense reports and uploading receipts. | `apps/expenses/index.html` (served statically) |
| Hana Inventory | Google Apps Script that audits the "Mizuho Inventory" Google Sheet and emails weekly alerts when counts drift. | `apps/hana-inventory/app` |
| Hotshot Quote Tool | Flask application with Alembic migrations and utilities for calculating freight quotes. | `apps/quote-tool/flask_app.py` |

Refer to each app's README for setup, testing, and deployment details:

- [`apps/expenses/README.md`](apps/expenses/README.md)
- [`apps/hana-inventory/APP_README.md`](apps/hana-inventory/APP_README.md)
- [`apps/quote-tool/README.md`](apps/quote-tool/README.md)

## Suggested next steps

1. Create `infra/` and `packages/` directories as shared components emerge (see `agents.md`).
2. Standardize Docker Compose workflows that build and run the apps together.
3. Add CI jobs that lint and test each application whenever the corresponding subtree changes.

## Contributing

Follow the branching, commit, and PR guidance in `agents.md`. When changing any application, update its documentation alongside
code changes and run the relevant test suites before committing.
