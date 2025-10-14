"""Tests covering BigQuery configuration helpers."""

from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import patch


def test_config_prefers_bigquery_when_components_set() -> None:
    """Verify ``Config`` assembles a BigQuery DSN when component env vars exist.

    The test injects temporary values for ``BIGQUERY_PROJECT``,
    ``BIGQUERY_DATASET``, and ``BIGQUERY_LOCATION`` alongside a blank
    ``DATABASE_URL`` using :func:`unittest.mock.patch.dict`. The assertion
    confirms that :mod:`config` builds the expected ``bigquery://`` SQLAlchemy
    URI. The helper takes no arguments and returns ``None`` because the
    behaviour is validated through ``assert`` statements.
    """

    environment = {
        "BIGQUERY_PROJECT": "quote-tool-472316",
        "BIGQUERY_DATASET": "quote_tool",
        "BIGQUERY_LOCATION": "us-central1",
    }
    with patch.dict(os.environ, environment, clear=False):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            sys.modules.pop("config", None)
            config_module = importlib.import_module("config")
            assert (
                config_module.Config.SQLALCHEMY_DATABASE_URI
                == "bigquery://quote-tool-472316/quote_tool?location=us-central1"
            )

    # Reload the configuration module after environment variables are restored.
    sys.modules.pop("config", None)
    importlib.import_module("config")
