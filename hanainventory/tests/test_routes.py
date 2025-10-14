from flask import template_rendered

from typing import Optional

import pytest

from app.data import BASELINE_INVENTORY, FORMS, ITEMS
from app.latest_inventory import LATEST_INVENTORY
from app.routes import _format_delta, _format_quantity


def test_format_quantity():
    assert _format_quantity(None) == "—"
    assert _format_quantity(3.0) == "3"
    assert _format_quantity(2.5) == "2.50"


def test_format_delta():
    assert _format_delta(None) == "—"
    assert _format_delta(0) == "0"
    assert _format_delta(3) == "+3"
    assert _format_delta(-1.5) == "-1.50"


def test_dashboard_context_contains_expected_data(client):
    recorded = []

    def _record(sender, template, context, **extra):  # pragma: no cover - signal handler
        recorded.append(context)

    template_rendered.connect(_record, client.application)
    response = client.get("/")
    template_rendered.disconnect(_record, client.application)

    assert response.status_code == 200
    assert recorded, "dashboard template should be rendered"

    context = recorded[0]
    network_rows = context["network_rows"]
    location_views = context["location_views"]

    expected_codes = set(LATEST_INVENTORY)
    assert len(network_rows) == len(ITEMS)
    assert len(location_views) == len(expected_codes)

    def _delta(expected: Optional[float], actual: Optional[float]) -> Optional[float]:
        if expected is None or actual is None:
            return None
        return actual - expected

    for view in location_views:
        code = view.location.code
        assert code in expected_codes
        baseline = BASELINE_INVENTORY.get(code, {})
        latest = LATEST_INVENTORY[code]

        expected_issue_count = 0
        for row in view.items:
            item_name = row.item.name
            expected_latest = latest.get(item_name)
            expected_baseline = baseline.get(item_name)

            if expected_latest is None:
                assert row.latest is None
            else:
                assert row.latest == pytest.approx(expected_latest)

            if expected_baseline is None:
                assert row.baseline is None
            else:
                assert row.baseline == pytest.approx(expected_baseline)

            expected_delta = _delta(expected_baseline, expected_latest)
            if expected_delta is None:
                assert row.delta is None
                if (expected_baseline is None) ^ (expected_latest is None):
                    expected_issue_count += 1
            else:
                assert row.delta == pytest.approx(expected_delta)
                if abs(expected_delta) > 1e-9:
                    expected_issue_count += 1

        assert view.issue_count == expected_issue_count

    # Verify that each network summary aggregates the latest quantities and
    # reports the appropriate delta against the expected totals.
    expected_totals = {item['label']: 0.0 for item in ITEMS}
    for latest in LATEST_INVENTORY.values():
        for label, value in latest.items():
            if value is not None:
                expected_totals[label] += value

    for summary in network_rows:
        expected_actual = expected_totals.get(summary.item.name)
        if expected_actual is None:
            assert summary.actual_total is None
            assert summary.delta is None
            continue

        assert summary.actual_total == pytest.approx(expected_actual)
        expected_total = summary.item.expected_total
        if expected_total is None:
            assert summary.delta is None
        else:
            assert summary.delta == pytest.approx(expected_actual - expected_total)
