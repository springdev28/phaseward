"""Support ``python -m qwave`` as well as the installed console script."""

from qwave.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
