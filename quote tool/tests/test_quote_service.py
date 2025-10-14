from services.quote import get_accessorial_options


def test_get_accessorial_options_excludes_guarantee_for_hotshot(
    seed_rates: None,
) -> None:
    """Hotshot quotes should omit the percentage-based Guarantee option."""
    options = get_accessorial_options("Hotshot")
    assert "Guarantee" not in options
    assert "Liftgate" in options


def test_get_accessorial_options_includes_guarantee_for_air(seed_rates: None) -> None:
    """Non-hotshot quotes should include the Guarantee accessorial."""
    options = get_accessorial_options("Air")
    assert "Guarantee" in options
