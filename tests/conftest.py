"""Keep headless Matplotlib test caches inside pytest's temporary directories."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def local_matplotlib_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Avoid writing caches outside the workspace or requiring a display."""
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "matplotlib"))
