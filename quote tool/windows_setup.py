"""Windows-specific launcher that interactively prepares environment files.

This script is tailored for the PyInstaller-based Windows distribution. It
guides the operator through generating a ``.env`` configuration, persists the
answers in the same format as the rest of the tooling (using
``dotenv.set_key``), initializes the database on first run, and finally starts
the Flask development server by importing :data:`flask_app.app`. The launcher
is safe to import in tests: all work happens inside :func:`main` and is guarded
by ``if __name__ == "__main__"``.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from getpass import getpass
from pathlib import Path
from typing import Dict, Mapping, MutableMapping, Sequence

from dotenv import dotenv_values, load_dotenv, set_key


class PromptAborted(RuntimeError):
    """Exception raised when the operator aborts an interactive prompt."""


REQUIRED_RATE_FILES: tuple[str, ...] = (
    "Hotshot_Rates.csv",
    "beyond_price.csv",
    "accessorial_cost.csv",
    "Zipcode_Zones.csv",
    "cost_zone_table.csv",
    "air_cost_zone.csv",
)

SENTINEL_FILENAME = ".windows_setup_complete"


def get_execution_dir() -> Path:
    """Return the directory that houses the executable or script.

    PyInstaller sets ``sys.frozen`` and points ``sys.executable`` at the bundled
    executable. When those attributes are absent, fall back to the directory of
    this source file. The resolved path is used for locating the ``.env`` file
    and the sentinel that marks the first run.
    """

    if getattr(sys, "frozen", False):  # PyInstaller sets this attribute.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_resource_root(base_dir: Path) -> Path:
    """Return the root directory that holds bundled PyInstaller resources.

    PyInstaller extracts data files to a temporary directory stored in
    ``sys._MEIPASS``. When running from source (for example during unit tests)
    the attribute is missing, so ``base_dir`` is returned instead. The helper is
    kept separate from :func:`get_execution_dir` because configuration files are
    written beside the executable, while data files ship with the frozen bundle.
    """

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass).resolve()
    return base_dir


def generate_secret_key() -> str:
    """Create a new Flask ``SECRET_KEY`` using ``secrets.token_urlsafe``."""

    return secrets.token_urlsafe(32)


def resolve_rate_data_dir(base_dir: Path) -> Path:
    """Determine where bundled CSV fixtures live relative to ``base_dir``.

    The packaged application may store CSV files directly beside the
    executable, under a ``rates`` folder, or within a ``resources`` bundle. When
    running a PyInstaller build the data files are unpacked beneath
    ``sys._MEIPASS``; :func:`get_resource_root` provides that directory so the
    lookup is resilient in both frozen and source-based environments. The first
    directory containing at least one known rate file is returned. If no matches
    are found, ``base_dir`` is used as a safe default so
    :func:`init_db.initialize_database` can still run (it tolerates missing
    files and logs warnings).
    """

    resource_root = get_resource_root(base_dir)
    search_roots: tuple[Path, ...]
    if resource_root != base_dir:
        search_roots = (resource_root, base_dir)
    else:
        search_roots = (base_dir,)

    candidate_dirs: list[Path] = []
    for root in search_roots:
        candidate_dirs.extend(
            (
                root / "rates",
                root / "resources" / "rates",
                root / "resources",
                root,
            )
        )

    for directory in candidate_dirs:
        if any((directory / name).exists() for name in REQUIRED_RATE_FILES):
            return directory
    return resource_root


def prompt_with_default(prompt_text: str, default: str | None) -> str:
    """Prompt for a value, allowing the operator to keep the existing default."""

    suffix = f" [{default}]" if default else ""
    try:
        return input(f"{prompt_text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt) as exc:  # pragma: no cover - defensive.
        raise PromptAborted from exc


def prompt_for_admin_email(existing: str | None) -> str:
    """Collect the administrator email address from stdin."""

    while True:
        response = prompt_with_default(
            "Enter the administrator email address", existing
        )
        if response:
            return response
        if existing:
            return existing
        print("Email is required for the initial administrator account.")


def prompt_for_admin_password(existing: str | None) -> str:
    """Collect the administrator password using :func:`getpass`."""

    while True:
        prompt = "Enter the administrator password"
        if existing:
            prompt += " (leave blank to keep current password)"
        prompt += ": "
        try:
            response = getpass(prompt).strip()
        except (EOFError, KeyboardInterrupt) as exc:  # pragma: no cover - defensive.
            raise PromptAborted from exc

        if response:
            return response
        if existing:
            return existing
        print("Password cannot be empty when configuring the administrator account.")


def prompt_for_google_maps_key(existing: str | None) -> str:
    """Collect the Google Maps API key used by address validation forms."""

    while True:
        response = prompt_with_default("Enter the Google Maps API key", existing)
        if response:
            return response
        if existing:
            return existing
        print("A Google Maps API key is required to enable mapping features.")


def prompt_for_secret_key(existing: str | None) -> str:
    """Collect or generate the Flask ``SECRET_KEY`` value."""

    prompt = "Enter the Flask SECRET_KEY"
    if existing:
        prompt += " (leave blank to keep current key)"
    else:
        prompt += " (leave blank to generate a new key)"
    response = prompt_with_default(prompt, None)
    if response:
        return response
    if existing:
        return existing
    secret = generate_secret_key()
    print("Generated a new SECRET_KEY for this installation.")
    return secret


def prompt_for_configuration(existing: Mapping[str, str]) -> Dict[str, str]:
    """Prompt the operator for environment values and return their answers."""

    results = {
        "ADMIN_EMAIL": prompt_for_admin_email(existing.get("ADMIN_EMAIL")),
        "ADMIN_PASSWORD": prompt_for_admin_password(existing.get("ADMIN_PASSWORD")),
        "GOOGLE_MAPS_API_KEY": prompt_for_google_maps_key(
            existing.get("GOOGLE_MAPS_API_KEY")
        ),
        "SECRET_KEY": prompt_for_secret_key(existing.get("SECRET_KEY")),
    }
    return results


def persist_configuration(env_path: Path, values: Mapping[str, str]) -> None:
    """Write the provided values to ``env_path`` using ``dotenv.set_key``."""

    env_path.touch(exist_ok=True)
    for key, value in values.items():
        set_key(str(env_path), key, value)


def load_environment(env_path: Path) -> MutableMapping[str, str]:
    """Load ``env_path`` and return the merged environment mapping."""

    load_dotenv(env_path, override=True)
    return os.environ


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point used by PyInstaller to configure and run the Flask app."""

    parser = argparse.ArgumentParser(description="Windows launcher for FSI Quote")
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Re-run the interactive prompts even if .env already exists.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    execution_dir = get_execution_dir()
    env_path = execution_dir / ".env"
    sentinel_path = execution_dir / SENTINEL_FILENAME

    existing_values = (
        {k: v for k, v in dotenv_values(env_path).items() if v is not None}
        if env_path.exists()
        else {}
    )
    should_prompt = args.reconfigure or not env_path.exists()

    if should_prompt:
        try:
            answers = prompt_for_configuration(existing_values)
        except PromptAborted:
            print("\nSetup aborted by user. Exiting without launching the server.")
            raise SystemExit(1)
        persist_configuration(env_path, answers)
        existing_values = answers

    load_environment(env_path)

    first_run = not sentinel_path.exists()
    if first_run:
        from init_db import initialize_database

        rate_data_dir = resolve_rate_data_dir(execution_dir)
        initialize_database(rate_data_dir)
        sentinel_path.touch()

    from flask_app import app

    app.run()


if __name__ == "__main__":
    main()
