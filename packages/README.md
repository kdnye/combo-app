# Shared packages

This directory hosts reusable Python packages shared across the Freight Services applications. Packages live in subdirectories using the standard `src`-less layout so they can be imported directly when the monorepo root is on the `PYTHONPATH` (the default when running tools from the repository root).

Add new shared modules here when multiple apps need the same code or domain models. Each package should include:

- An `__init__.py` that re-exports the public API.
- Docstrings describing the purpose of the package and its modules.
- Tests collocated with the consumer application or under the package itself when the utilities are app-agnostic.

See `packages/fsi_common` for the shared domain models used by the Expenses application.
