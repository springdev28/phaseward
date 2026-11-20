# PROMPT 0 validation — 18 November 2026

Stage 0 is complete: the package files exist, the editable install works, the
test suite passed, and the three initial commands executed locally. No physical
transport model or solver was implemented.

## Environment

- Native Apple Silicon process: arm64, Darwin 25.6.0, 8 logical CPUs, 64-bit CPython.
- Python 3.13.0; qwave 0.1.0; NumPy 2.5.5; SciPy 1.18.1;
  Matplotlib 3.11.2; pytest 9.2.0.
- Runtime pip 24.2. Setuptools was an isolated build dependency, not a runtime
  dependency; its runtime version is correctly recorded as null.
- The additional regular wheel build used existing system Python 3.13.0 and
  setuptools 82.0.1 without installing anything into system Python.

The initial `pip install -e '.[dev]'` attempt could not resolve PyPI inside the
restricted execution sandbox. Retrying the same local virtual-environment
installation with permitted network access and `--no-cache-dir` succeeded.
The installed package requires no accounts, paid services, cloud compute, or
containers. Drive access was used only to inspect the supplied project documents.

## Tests and exact output

Executed from the workspace:

```sh
source .venv/bin/activate
pytest
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.0, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/baharyuksel/Documents/ChatGPT/Phaseward
configfile: pyproject.toml
testpaths: tests
collected 44 items

tests/test_cli.py .......                                                [ 15%]
tests/test_config.py ..........................                          [ 75%]
tests/test_demo.py ...........                                           [100%]

============================= 44 passed in 30.63s ==============================
```

Checks cover independent analytical trapezoidal error, second-order grid
convergence, local seeded RNG reproducibility, JSON rejection paths, installed
CLI/module entry points outside the checkout, CPU/package diagnostics, public
output round trips, provenance and hashes, existing-directory protection, and a
headless PNG export. No test is presented as validation of electron transport.

## Executed commands and outcomes

The complete shell command record, including inspection, the failed installation
attempt, the successful retry, and the wheel check, is in
[command_log.md](command_log.md).

```sh
source .venv/bin/activate
qwave doctor --dev
qwave config-check examples/demo.json
MPLCONFIGDIR="$PWD/results/.matplotlib-cache" qwave demo --config examples/demo.json --output results/stage0-demo --plot
python -m pip check
```

- Doctor: exit 0; `ok`, `runtime_ready`, and `development_ready` are true.
- Config check: exit 0; `valid` is true; all settings match the example.
- Demo: exit 0; produced the actual bundle at `results/stage0-demo/`.
- Dependency check: `No broken requirements found.`
- `git check-ignore` confirmed both results and the virtual environment are ignored.
- A regular wheel built successfully; ZIP inspection verified package code,
  the typed-package marker, console entry point, and MIT license (22 entries).
- The plot was inspected visually: axes are dimensionless and its title explicitly
  labels it a numerical placeholder with no electron-scattering model.

The sandbox denied Matplotlib's usual home cache path during the first doctor
run; Matplotlib used a temporary cache and passed its import check. For the
saved demo the command above explicitly uses a writable, ignored local cache.
Tests also use temporary cache directories. This is not a dependency failure.

## Measured sample output

Read directly from `results/stage0-demo/metrics.json`:

```json
{
  "monte_carlo_absolute_error": 0.010858854787712091,
  "monte_carlo_integral": 0.3224744785456212,
  "reference_integral": 0.3333333333333333,
  "trapezoid_absolute_error": 2.5431315104351704e-06,
  "trapezoid_integral": 0.33333587646484375
}
```

These are polynomial-integration values, not physical findings. The run used seed
1729, 257 grid points, and 1,024 uniform samples. Its recorded elapsed time before
writing the manifest was 15.730632958002388 seconds, including plotting and
first-use font-cache work; this is not a solver performance benchmark.

The bundle contains `config.json`, `metrics.json`, `grid.csv`, `samples.csv`,
`arrays.npz`, `demo.png`, and `manifest.json`. The manifest was written before
an initial Git commit existed, so its commit is explicitly null and its working
tree is dirty. Source SHA-256
`c5d64f665471c7dbcb42f1b8d0b2758d28d21d77e0b7687eff79bfdac63ecd09`
and per-file hashes identify the executed package snapshot.

## Installed environment snapshot

Actual output of `.venv/bin/python -m pip freeze --all`:

```text
contourpy==1.4.0
cycler==0.12.1
fonttools==4.68.0
iniconfig==2.3.1
kiwisolver==1.5.1
matplotlib==3.11.2
numpy==2.5.5
packaging==26.3
pillow==13.0.0
pip==24.2
pluggy==1.7.0
Pygments==2.21.0
pyparsing==3.3.3
pytest==9.2.0
python-dateutil==4.0.0
# Editable Git install with no remote (qwave==0.1.0)
-e /Users/baharyuksel/Documents/ChatGPT/Phaseward
scipy==1.18.1
tzdata==2026.6
```

## Blockers and limits

There are no unresolved blockers for PROMPT 0. Python 3.11+ is declared, but only
Python 3.13.0 on this arm64 Mac was executed in this stage. Reproduction across
different numerical-library versions is not claimed to be bitwise identical.
Only the dimensionless demonstration is implemented; stationary scattering,
wave packets, physical disorder, sensitivity optimization, held-out experiments,
and the Streamlit GUI remain future work. The hypothesis, physical accuracy,
and novelty remain untested.

