"""Minimal standalone Flask API for quote generation.

This module exposes two endpoints:
* ``POST /api/quote`` - Create a new quote by providing shipment details
  in JSON format. The endpoint returns the calculated quote information.
* ``GET /api/quote/<quote_id>`` - Retrieve a previously generated quote
  by its ``quote_id``.

The implementation reuses the existing service layer so that it shares the
same business logic and database models as the main application.  It is
useful for scripts or environments where the full web interface is not
required.
"""

from __future__ import annotations

from flask import Flask, jsonify, request
import json
from services import quote as quote_service

app = Flask(__name__)


@app.post("/api/quote")
def api_create_quote():
    """Generate a quote from JSON payload.

    Expected JSON fields:
    ``user_id`` and ``user_email`` identify the requesting user.  The
    remaining shipment fields include:

    - ``quote_type`` (``"Hotshot"`` or ``"Air"``)
    - ``origin`` / ``destination`` ZIP codes
    - ``weight`` (actual weight in pounds)
    - ``pieces`` and package ``length``/``width``/``height`` (inches) used
      to calculate dimensional weight
    - ``accessorials`` list (optional)

    Any unspecified numeric values default to ``0`` (or ``1`` for pieces).
    """

    data = request.get_json() or {}

    quote_type = data.get("quote_type", "Hotshot")
    if quote_type not in {"Hotshot", "Air"}:
        return jsonify({"error": "Invalid quote_type"}), 400

    result = quote_service.create_quote(
        data.get("user_id"),
        data.get("user_email"),
        quote_type,
        data.get("origin"),
        data.get("destination"),
        data.get("weight", 0),
        pieces=data.get("pieces", 1),
        length=data.get("length", 0.0),
        width=data.get("width", 0.0),
        height=data.get("height", 0.0),
        dim_weight=data.get("dim_weight", 0.0),
        accessorials=data.get("accessorials", []),
    )

    if isinstance(result, tuple):
        quote_obj, metadata = result
    else:  # backward compatibility
        quote_obj, metadata = result, {}

    payload = {
        "quote_id": quote_obj.quote_id,
        "quote_type": quote_obj.quote_type,
        "origin": quote_obj.origin,
        "destination": quote_obj.destination,
        "weight": quote_obj.weight,
        "weight_method": quote_obj.weight_method,
        "actual_weight": quote_obj.actual_weight,
        "dim_weight": quote_obj.dim_weight,
        "pieces": quote_obj.pieces,
        "total": quote_obj.total,
        "metadata": metadata,
    }
    return jsonify(payload), 201


@app.get("/api/quote/<quote_id>")
def api_get_quote(quote_id: str):
    """Return previously generated quote as JSON."""

    quote_obj = quote_service.get_quote(quote_id)
    if quote_obj is None:
        return jsonify({"error": "Quote not found"}), 404

    metadata = {}
    try:
        if quote_obj.quote_metadata:
            metadata = json.loads(quote_obj.quote_metadata)
    except Exception:
        metadata = {}

    payload = {
        "quote_id": quote_obj.quote_id,
        "quote_type": quote_obj.quote_type,
        "origin": quote_obj.origin,
        "destination": quote_obj.destination,
        "weight": quote_obj.weight,
        "weight_method": quote_obj.weight_method,
        "actual_weight": quote_obj.actual_weight,
        "dim_weight": quote_obj.dim_weight,
        "pieces": quote_obj.pieces,
        "total": quote_obj.total,
        "metadata": metadata,
    }
    return jsonify(payload)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    app.run(debug=True)
