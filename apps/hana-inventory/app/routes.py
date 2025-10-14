from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from flask import Blueprint, current_app, render_template, url_for
from werkzeug.routing import BuildError
from sqlalchemy.orm import joinedload

from .models import Item, Location, LocationItem

bp = Blueprint('main', __name__)


@dataclass
class NetworkSummaryRow:
    item: Item
    image_url: str | None
    actual_total: float | None
    delta: float | None


@dataclass
class LocationRow:
    item: Item
    image_url: str | None
    latest: float | None
    baseline: float | None
    delta: float | None
    sheet_column: str | None


@dataclass
class LocationView:
    location: Location
    issue_count: int
    items: List[LocationRow]


@dataclass
class AppLink:
    """Metadata describing an application that should be shown on the home page."""

    slug: str
    name: str
    description: str
    url: str
    external: bool


def _format_quantity(value: float | None) -> str:
    if value is None:
        return '—'
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"


def _format_delta(value: float | None) -> str:
    if value is None:
        return '—'
    prefix = '+' if value > 0 else ''
    return f"{prefix}{_format_quantity(value)}"


_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.gif')


def _slugify_item_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", '-', name.lower()).strip('-')
    return slug or 'item'


def _item_image_url_cache(items: List[Item]) -> Dict[int, str | None]:
    static_folder = Path(current_app.static_folder or Path(current_app.root_path) / 'static')
    cache: Dict[int, str | None] = {}
    for item in items:
        slug = _slugify_item_name(item.name)
        image_url: str | None = None
        for extension in _IMAGE_EXTENSIONS:
            relative_path = Path('images') / f"{slug}{extension}"
            if (static_folder / relative_path).exists():
                image_url = url_for('static', filename=str(relative_path).replace('\\', '/'))
                break
        cache[item.id] = image_url
    return cache


def _load_app_links(raw_links: Iterable[dict]) -> List[AppLink]:
    """Convert configuration dictionaries into :class:`AppLink` objects.

    Parameters
    ----------
    raw_links:
        Iterable of dictionaries loaded from :data:`flask.current_app.config`
        describing each application. Expected keys are ``slug``, ``name``,
        ``description``, and either ``url`` or ``endpoint``. Optional keys
        include ``external`` to flag whether the link should open in a new tab.

    Returns
    -------
    List[AppLink]
        Normalized collection of app metadata that the template can iterate
        over. Invalid entries are skipped after emitting a warning via the
        Flask application logger.
    """

    app_links: List[AppLink] = []
    for link in raw_links:
        slug = link.get('slug')
        name = link.get('name')
        description = link.get('description')
        endpoint = link.get('endpoint')
        url = link.get('url')
        external = link.get('external', True)

        if endpoint:
            try:
                url = url_for(str(endpoint))
                external = False
            except BuildError:
                current_app.logger.warning(
                    'Skipping app directory entry because endpoint %s cannot be built.',
                    endpoint,
                )
                continue

        if not all([slug, name, description, url]):
            current_app.logger.warning(
                'Skipping app directory entry because it is missing required fields: %s',
                link,
            )
            continue

        app_links.append(
            AppLink(
                slug=str(slug),
                name=str(name),
                description=str(description),
                url=str(url),
                external=bool(external),
            )
        )
    return app_links


@bp.route('/')
def home() -> str:
    """Render the unified landing page for all Freight Services applications.

    Returns
    -------
    str
        HTML for the home view listing each tool configured in
        :data:`flask.current_app.config`.
    """

    raw_links = current_app.config.get('APP_DIRECTORY', [])
    apps = _load_app_links(raw_links)
    return render_template('home.html', apps=apps)


@bp.route('/hana-inventory')
@bp.route('/hana-inventory/')
def inventory_dashboard() -> str:
    """Render the Hana Table Inventory dashboard.

    Returns
    -------
    str
        HTML representing the existing inventory dashboard, including
        aggregated network totals and per-location snapshots.
    """

    items = (
        Item.query.order_by(Item.display_order)
        .options(joinedload(Item.locations))
        .all()
    )
    image_urls = _item_image_url_cache(items)
    locations = (
        Location.query.options(joinedload(Location.items).joinedload(LocationItem.item))
        .order_by(Location.code)
        .all()
    )

    network_rows: List[NetworkSummaryRow] = []
    for item in items:
        quantities: List[float] = []
        for location in locations:
            for loc_item in location.items:
                if loc_item.item_id == item.id and loc_item.latest_quantity is not None:
                    quantities.append(loc_item.latest_quantity)
        actual_total = sum(quantities) if quantities else None
        delta = (
            actual_total - item.expected_total
            if actual_total is not None and item.expected_total is not None
            else None
        )
        network_rows.append(
            NetworkSummaryRow(
                item=item,
                image_url=image_urls.get(item.id),
                actual_total=actual_total,
                delta=delta,
            )
        )

    location_views: List[LocationView] = []
    for location in locations:
        items_by_id = {loc_item.item_id: loc_item for loc_item in location.items}
        rows: List[LocationRow] = []
        issue_count = 0
        for item in items:
            loc_item = items_by_id.get(item.id)
            latest = loc_item.latest_quantity if loc_item else None
            baseline = loc_item.baseline_quantity if loc_item else None
            delta = None
            if latest is not None and baseline is not None:
                delta = latest - baseline
                if abs(delta) > 1e-9:
                    issue_count += 1
            elif latest is not None or baseline is not None:
                issue_count += 1
            rows.append(
                LocationRow(
                    item=item,
                    image_url=image_urls.get(item.id),
                    latest=latest,
                    baseline=baseline,
                    delta=delta,
                    sheet_column=loc_item.sheet_column if loc_item else None,
                )
            )
        location_views.append(LocationView(location=location, issue_count=issue_count, items=rows))

    return render_template(
        'dashboard.html',
        network_rows=network_rows,
        location_views=location_views,
        format_quantity=_format_quantity,
        format_delta=_format_delta,
    )
