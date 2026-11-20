# Phaseward PROMPT 1 validation — 18 November 2026

The first scientific component is implemented: stationary, elastic, coherent
one-dimensional scattering with a configurable constant effective mass and real
potential. The project is named Phaseward; the package and CLI remain `qwave`.
The installed version is 0.2.0. No wave-packet fidelity or optimization is claimed.

## Executed environment and package

Python 3.13.0 on native arm64 Darwin 25.6.0, with eight logical CPUs. Runtime
versions: NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, pytest 9.2.0. The existing
system setuptools 82.0.1 built a local wheel; no new runtime dependencies, cloud
services, paid APIs, Docker, notebooks, or GUI framework were added.

An early import probe found the previous editable install's `.pth` file had the
macOS hidden flag. Python 3.13 explicitly skips hidden `.pth` files. Removing the
flag made that invocation work, but a subsequent invocation saw the same import
failure. The final environment therefore uses a standard locally built wheel,
which avoids `.pth` processing. This repair required no network access. The final
CLI, full tests, and studies ran **without PYTHONPATH overrides**. A separate audit
compared every installed Python module byte for byte with `src/qwave/`.

The installed wheel's code SHA-256 identity is
`f517d4a2b3ad0ce69a7ded5667f3dd96c3818cee044674c6d82c3dae0715b309`. The run manifests identify this actual installed
code, with Git identity unavailable for the wheel. The repository remains
uncommitted. Earlier stage-0 results and documentation are preserved unchanged.

## Exact installation and validation commands

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage1-wheels .
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage1-wheels/qwave-0.2.0-py3-none-any.whl
.venv/bin/qwave --version
mkdir -p results/stage1-logs
```

The independent test, CLI, and validation jobs used these exact shell inputs:

```sh
set -o pipefail
source .venv/bin/activate
pytest | tee results/stage1-logs/pytest.txt
```

```sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage1-cli"
qwave doctor --dev > results/stage1-logs/doctor.json
qwave config-check examples/demo.json > results/stage1-logs/demo-config-check.json
qwave config-check examples/barrier.json > results/stage1-logs/barrier-config-check.json
qwave demo --config examples/demo.json --output results/stage1-demo
qwave scatter --config examples/barrier.json --output results/stage1-barrier
python -m pip check
```

```sh
set -o pipefail
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage1-validation"
python examples/validate_scattering.py --output results/stage1-validation | tee results/stage1-logs/validation.txt
```

The preliminary targeted command was
`PYTHONPATH=src .venv/bin/pytest tests/test_scattering.py tests/test_scatter_workflow.py`
(41 passed in 18.76 seconds). That source-path override was used only during
implementation while repairing the old installation. The full final suite below
exercised the installed wheel. Doctor and both config checks exited 0; the fresh
demo, scatter, and convergence study exited 0. `pip check` reported
`No broken requirements found.`

## Full test output

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.0, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/baharyuksel/Documents/ChatGPT/Phaseward
configfile: pyproject.toml
testpaths: tests
collected 85 items

tests/test_cli.py .......                                                [  8%]
tests/test_config.py ..........................                          [ 38%]
tests/test_demo.py ...........                                           [ 51%]
tests/test_scatter_workflow.py ...................                       [ 74%]
tests/test_scattering.py ......................                          [100%]

============================= 85 passed in 19.93s ==============================
```

The 85 tests include the previous 44 infrastructure tests plus 41 scattering and
workflow tests. Scientific checks include discrete free-channel complex phase,
continuum free-phase convergence, analytical rectangular barriers below/at/above
the top, independent Gaussian ODE matching of both complex amplitudes, an exact
unequal-lead discrete step, opaque tunneling, all supported potential profiles,
invalid band energies, probability conservation, and phase masking. Export checks
cover complex CSV/NPZ round trips, artifact hashes, and headless figure creation.

## Analytical and independent-method outcomes

All nine checks in the reproducible validation driver passed:

- `free_discrete_complex_phase`: **PASS**
- `conservation`: **PASS**
- `linear_residual`: **PASS**
- `rectangle_probability_finest`: **PASS**
- `rectangle_complex_t_finest`: **PASS**
- `gaussian_complex_t_finest`: **PASS**
- `gaussian_complex_r_finest`: **PASS**
- `second_order_complex_amplitude_convergence`: **PASS**
- `ode_tolerance_tightening`: **PASS**

No analytical benchmark failed. Coarse-grid departures from continuum answers
are retained and reported as numerical errors, not concealed or reclassified as
physical effects. The exact discrete free-channel check and continuum convergence
check test different statements: the former checks the implementation of the
chosen discretization, while the latter measures its approximation to the PDE.

For the 40 meV, 10 nm rectangular barrier, domain [-40,40] nm, mass ratio 0.067,
and energies [5,10,20,39,40,41,60,100] meV:

| Spacing (nm) | Max absolute error in T | Max complex-amplitude error in t | Max conservation error |
| --- | --- | --- | --- |
| 1 | 0.00667974413 | 0.233463236 | 5.329e-15 |
| 0.5 | 0.00165292462 | 0.0576422187 | 2.154e-14 |
| 0.25 | 0.000412177931 | 0.0143606527 | 2.62e-14 |
| 0.125 | 0.000102978813 | 0.00358697571 | 6.883e-14 |
| 0.0625 | 2.57406009e-05 | 0.000896543655 | 7.86e-14 |

The complex-amplitude error decreases by approximately four on each halving of
spacing. The free-channel and Gaussian studies show the same measured trend.
These are results for the specified grids, domains, and energies, not a universal
convergence guarantee for arbitrary discontinuities or unresolved resonances.

The Gaussian cross-check uses a 20 meV peak, sigma=3 nm, domain [-30,30] nm,
and energies [10,25,50,80] meV. At 0.0625 nm spacing, the largest complex errors are
`0.000491317123104` in t and
`3.67799724001e-05` in r. The continuum DOP853
reference is separately coded and tightened from (rtol=1e-11, atol=1e-13) to
(1e-12, 1e-14); the largest resulting amplitude change is
`1.26617738739e-11`. This supports treating the
finite-difference error as dominant for these comparisons, but it is not a
rigorous interval bound on the ODE result.

## Why the numerical tolerances are used

- Conservation guard in tests: 1e-10; the largest measured study residual
  `|T+R-1|` is 8.65973959208e-14. This allows
  platform/roundoff variation while detecting flux-normalization regressions.
- Scaled linear-residual guard: 1e-14; the largest measured value is
  2.50578408691e-16.
- At dx=0.0625 nm, rectangle regression limits are 4e-5 for T and 1.1e-3 for
  complex t. Gaussian limits are 6e-4 for t and 5e-5 for r. These limits are
  informed by the displayed convergence measurements and apply only to those
  fixed validation configurations.
- The CLI example's configurable 1e-8 conservation alert is a permissive runtime
  diagnostic, not a claim of 1e-8 continuum accuracy. A coarse grid can conserve
  flux almost perfectly while having appreciable phase error.
- The expected factor-four refinement behavior is a regression check of the
  numerical approximation, not a hard-coded improvement in a research method.

## Saved example and figures

`results/stage1-barrier/` contains eight inventoried outputs plus its manifest:
`config.json`, `diagnostics.json`, `potential.csv`, `scattering.csv`, `arrays.npz`,
and `scattering.png`, `scattering.svg`, `scattering.pdf`. The configuration is the
checked-in `examples/barrier.json`: 801 nodes (0.1 nm), 477 energies from 1 to
120 meV, the same rectangular barrier, and mass ratio 0.067.

Its measured maximum `|T+R-1|` is
`8.79296635503e-14`, with maximum scaled
linear residual `2.02261946403e-16`.
There were 0 masked phase points.

`results/stage1-validation/` preserves the raw arrays for every spatial grid,
continuum reference arrays, `convergence.csv`, `report.json`, PNG/SVG/PDF figures,
and a manifest with exact parameters, constants, versions, code/driver hashes,
seed status, approximations, and artifact checksums. Both figures were visually
inspected for clear axes, units, labels, and phase conventions; their underlying
numerical validation is independent of their appearance. All saved artifact
hashes were recomputed successfully.

Recorded elapsed times before writing manifests were
18.420040 seconds for the barrier run and
19.496272 seconds for validation. They
include plotting and first-use font-cache work and were run alongside tests;
they are not isolated solver performance benchmarks.

## Files and scope

Implemented/extended `scattering`, `potentials`, `units`, `config`, `experiments`,
`plotting`, `cli`, and version metadata; added independent `references`, the
barrier configuration, validation driver, scientific tests, and model documentation.
Updated project naming, README, architecture, and AGENTS stage instructions.
See [architecture.md](architecture.md) for the current module map and file tree.

## Remaining limitations and blockers

There are no unresolved PROMPT 1 blockers. Validation covers the stated modest
benchmarks, not all possible potentials or resonances. Both leads must propagate;
closed outgoing channels are explicitly rejected. Mass is constant. Finite lead
bands, grid sampling, and finite-domain replacement by ideal leads are explicit
numerical approximations. Phase at underflowing transmission is unresolved, and
energy sampling needs independent refinement for sharp resonances. Only Python
3.13.0 on this arm64 Mac was executed. No claims are made about packet fidelity,
robustness, optimization, novelty, or real semiconductor devices.

The current `.venv` uses the recorded wheel install. After future source changes,
rebuild/reinstall before running installed-package checks, or establish a working
editable install and verify its import path. The source tree and installed code
must agree; a stale installed wheel must never be mistaken for tested new code.
