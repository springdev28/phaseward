"""Start Phaseward locally: streamlit run app.py (from this directory)."""

from pathlib import Path
import os

workspace = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(workspace / "results" / ".matplotlib-gui"))

from qwave.gui import main

main(workspace)
