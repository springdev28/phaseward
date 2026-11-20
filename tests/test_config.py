"""Configuration validation must reject ambiguity and unsupported physics."""

import json
from pathlib import Path

import pytest

from qwave.config import ConfigError, DemoConfig, load_config


def test_example_matches_resolved_defaults() -> None:
    """The checked-in quickstart configuration is executable and fully explicit."""
    example = Path(__file__).resolve().parents[1] / "examples" / "demo.json"
    assert load_config(example) == DemoConfig()


@pytest.mark.parametrize(("field", "value"), [
    ("schema_version", 2), ("schema_version", True),
    ("experiment", "scattering"), ("unit_system", "SI"),
    ("seed", -1), ("seed", 2**64), ("seed", True), ("seed", 1.5),
    ("grid_points", 1), ("grid_points", 1_000_002), ("grid_points", "257"),
    ("monte_carlo_samples", 0), ("monte_carlo_samples", 1_000_001),
    ("monte_carlo_samples", None),
])
def test_invalid_values_are_rejected(field: str, value: object) -> None:
    """Reject bool-as-integer, invalid sizes, wrong units, and unimplemented models."""
    settings = DemoConfig().to_dict()
    settings[field] = value
    with pytest.raises(ConfigError):
        DemoConfig.from_mapping(settings)


@pytest.mark.parametrize("unknown", [True, False])
def test_unknown_or_missing_fields_are_rejected(unknown: bool) -> None:
    """A typo or incomplete file must not silently select default settings."""
    settings = DemoConfig().to_dict()
    if unknown:
        settings["grid_point"] = 100
    else:
        del settings["seed"]
    with pytest.raises(ConfigError, match="configuration fields"):
        DemoConfig.from_mapping(settings)


@pytest.mark.parametrize("text", [
    '{"seed": 1, "seed": 2}', '{"seed": NaN}', '{"seed": Infinity}',
    '{"seed": -Infinity}', "[]", "null", "{broken",
])
def test_ambiguous_or_malformed_json_is_rejected(tmp_path: Path, text: str) -> None:
    """Reject duplicates, non-finite constants, invalid roots, and syntax errors."""
    path = tmp_path / "invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_missing_file_and_invalid_utf8_are_user_errors(tmp_path: Path) -> None:
    """Filesystem and encoding failures receive configuration context."""
    path = tmp_path / "missing.json"
    with pytest.raises(ConfigError, match="cannot read configuration"):
        load_config(path)
    path.write_bytes(b"\xff")
    with pytest.raises(ConfigError, match="cannot read configuration"):
        load_config(path)


def test_seed_extremes_and_small_sizes_are_valid(tmp_path: Path) -> None:
    """The supported bounds round-trip through JSON without truncation."""
    config = DemoConfig(seed=2**64 - 1, grid_points=2, monte_carlo_samples=1)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config.to_dict()), encoding="utf-8")
    assert load_config(path) == config
