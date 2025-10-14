"""Workspace blueprint that promotes the quote tool as the primary app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from flask import Blueprint, current_app, render_template, url_for
from flask_login import login_required
from flask.typing import ResponseReturnValue
from werkzeug.routing import BuildError

workspace_bp = Blueprint("workspace", __name__, url_prefix="/workspace")


@dataclass
class WorkspaceApp:
    """Metadata describing an application link shown on the workspace page."""

    slug: str
    name: str
    description: str
    url: str
    external: bool
    primary: bool = False
    cta_label: str = "Open"


def _normalize_app_entries(raw_entries: Iterable[dict]) -> List[WorkspaceApp]:
    """Convert configuration dictionaries into :class:`WorkspaceApp` objects.

    Args:
        raw_entries: Iterable of dictionaries loaded from
            :data:`flask.current_app.config` describing each application. Each
            dictionary should include ``slug``, ``name``, ``description`` and
            either ``url`` or ``endpoint``. Optional keys are ``external``,
            ``primary`` and ``cta_label``.

    Returns:
        List[WorkspaceApp]: Normalised metadata that can be rendered by
        templates. Invalid entries are skipped after emitting a warning.

    External Dependencies:
        * :func:`flask.url_for` when resolving internal endpoints.
        * :data:`flask.current_app.logger` to log configuration mistakes.
    """

    apps: List[WorkspaceApp] = []
    for entry in raw_entries:
        slug = entry.get("slug")
        name = entry.get("name")
        description = entry.get("description")
        endpoint = entry.get("endpoint")
        url = entry.get("url")
        external = bool(entry.get("external", True))
        primary = bool(entry.get("primary", False))
        cta_label = str(entry.get("cta_label", "Open"))

        if endpoint:
            try:
                url = url_for(str(endpoint))
                external = False
            except BuildError:
                current_app.logger.warning(
                    "Skipping workspace entry because endpoint %s cannot be built.",
                    endpoint,
                )
                continue

        if not all([slug, name, description, url]):
            current_app.logger.warning(
                "Skipping workspace entry because it is missing required fields: %s",
                entry,
            )
            continue

        apps.append(
            WorkspaceApp(
                slug=str(slug),
                name=str(name),
                description=str(description),
                url=str(url),
                external=external,
                primary=primary,
                cta_label=cta_label,
            )
        )

    return apps


@workspace_bp.route("/", methods=["GET"])
@login_required
def home() -> ResponseReturnValue:
    """Render the workspace landing page that links every internal tool.

    Returns:
        ResponseReturnValue: HTML produced from ``workspace/index.html`` with
        the configured application metadata in context.

    External Dependencies:
        * :func:`_normalize_app_entries` to interpret configuration.
        * :func:`flask.render_template` to produce the HTML response.
    """

    raw_entries = current_app.config.get("WORKSPACE_APPS", [])
    apps = _normalize_app_entries(raw_entries)
    primary_app = next((app for app in apps if app.primary), None)
    supporting_apps = [app for app in apps if not app.primary]
    return render_template(
        "workspace/index.html",
        primary_app=primary_app,
        supporting_apps=supporting_apps,
    )


__all__ = ["workspace_bp", "WorkspaceApp", "_normalize_app_entries"]
