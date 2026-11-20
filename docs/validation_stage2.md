# Phaseward PROMPT 2 validation — 18 November 2026

Implemented and installed qwave **0.3.0** in the existing Phaseward workspace.
The packet layer preserves stage-1 scattering conventions, normalizes the incoming
energy amplitude, reports throughput separately from conditional fidelity,
offers a declared bounded delay search, and optionally reconstructs lead states
with the energy–wave-number Jacobian. Equations and limits are derived in
[mathematics.md](mathematics.md). No additional dependencies or GUI were added.

## Environment and installed-code verification

Executed locally on native arm64 Darwin 25.6.0, eight logical CPUs, with Python
3.13.0, NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, and pytest 9.2.0. The existing
system build backend produced the wheel offline. Tests and final runs used the
installed wheel without a `PYTHONPATH` override. All 17 installed Python modules
were compared byte for byte with `src/qwave/` and matched.

Installed code identity:
`c235f64ca33b8af889fe014c9dde5a1f7bc851a8e8149423669ff9034bffc844`.
Wheel SHA-256:
`a737095b5f91df352d080509629191cf6880b83504ea57a7cf9d52f5f2a8ec3b`.
All final manifests record the same installed source identity and actual software
versions. The repository remains uncommitted; no Git commit was fabricated.

The regular wheel install retains the stage-1 workaround for this Mac's hidden
editable-install `.pth` file. Source changes require a new wheel build/install,
or a repaired editable install whose import location is verified. No runtime
network access, account, Docker, GPU, paid API, or physical device is needed.
Only Python 3.13.0 on this machine was executed; the declared support floor is 3.11.

## Exact final commands

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.
New files and edits were made with `apply_patch`. Source inspection used `rg`,
`cat`, and `sed`; existing stage-0 and stage-1 bundles were preserved.

```sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage2-wheels .
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage2-wheels/qwave-0.3.0-py3-none-any.whl
mkdir -p results/stage2-logs
.venv/bin/qwave --version
```

The version command printed `qwave 0.3.0`. The installed-source audit was:

```sh
.venv/bin/python - <<'PY' > results/stage2-logs/source-audit.json
from pathlib import Path
import json
import qwave
from qwave.provenance import source_identity

installed = Path(qwave.__file__).parent
assert '.venv/lib/' in str(installed), installed
sources = sorted(Path('src/qwave').glob('*.py'))
for source in sources:
    assert source.read_bytes() == (installed/source.name).read_bytes(), source
print(json.dumps({'version': qwave.__version__, 'installed_path': str(installed),
                  'matching_python_modules': len(sources), 'source': source_identity()}, indent=2))
PY
```

An earlier ad hoc audit successfully compared the same files but then attempted
to print a nonexistent `code_sha256` dictionary key. That reporting probe raised
`KeyError`; the corrected audit above uses the actual `sha256` field. This was
not a solver or test failure. The pip cache permission warning was non-blocking;
the wheel installation and `pip check` succeeded.

The following three jobs ran concurrently, with independent output directories:

```sh
set -o pipefail
source .venv/bin/activate
pytest | tee results/stage2-logs/pytest.txt
```

```sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage2-cli"
qwave doctor --dev > results/stage2-logs/doctor.json
qwave config-check examples/demo.json > results/stage2-logs/demo-config-check.json
qwave config-check examples/barrier.json > results/stage2-logs/barrier-config-check.json
qwave config-check examples/wavepacket.json > results/stage2-logs/packet-config-check.json
qwave demo --config examples/demo.json --output results/stage2-demo --plot > results/stage2-logs/demo.txt
qwave scatter --config examples/barrier.json --output results/stage2-barrier > results/stage2-logs/scatter.txt
qwave packet --config examples/wavepacket.json --output results/stage2-packet > results/stage2-logs/packet.txt
python -m pip check > results/stage2-logs/pip-check.txt
```

```sh
set -e
set -o pipefail
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage2-validation"
python examples/validate_packets.py --output results/stage2-validation | tee results/stage2-logs/packet-validation.txt
python examples/validate_scattering.py --output results/stage2-scattering-validation | tee results/stage2-logs/scattering-validation.txt
```

All commands in these jobs exited successfully. Doctor reported `ok: true`,
all three configuration checks reported `valid: true`, and `pip check` printed
`No broken requirements found.` The writable Matplotlib cache locations avoid
the sandbox's read-only home cache. Initial font-cache building is included in
wall-clock times; these runs are not isolated performance benchmarks.

During implementation the targeted source-tree check was
`PYTHONPATH=src .venv/bin/pytest tests/test_wavepackets.py tests/test_packet_workflow.py`:
36 passed in 18.26 seconds on the final source before installation. Preliminary
device and synthetic runs remain in `results/stage2-packet-development/` and
`results/stage2-validation-development/`; their metadata distinguishes the
development source from the final installed runs.

## Full installed-package test output

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.0, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/baharyuksel/Documents/ChatGPT/Phaseward
configfile: pyproject.toml
testpaths: tests
collected 121 items

tests/test_cli.py .......                                                [  5%]
tests/test_config.py ..........................                          [ 27%]
tests/test_demo.py ...........                                           [ 36%]
tests/test_packet_workflow.py ..............                             [ 47%]
tests/test_scatter_workflow.py ...................                       [ 63%]
tests/test_scattering.py ......................                          [ 81%]
tests/test_wavepackets.py ......................                         [100%]

============================= 121 passed in 19.53s =============================
```

The 36 new tests cover Gaussian truncation and amplitude normalization, positive
nonuniform quadrature, actual-equals-target outputs, global phase, signed delays,
bounded alignment, quadratic phase, amplitude filtering, tiny/zero/subnormal
throughput, zero targets, undefined/disabled/flat-scan handling, independent
quadrature convergence, spatial Parseval checks, and an analytic complex
position-space Gaussian. Workflow tests cover strict schemas, resolution guards,
CLI execution, all output formats, exact saved settings, complex data round trips,
hashes, optional reconstruction, and refusal to overwrite results.

All 85 earlier infrastructure/scattering tests also passed. The rerun of the
independent stationary study passed all nine checks, including below/at/above
barrier transmission, complex free phase, Gaussian ODE cross-checks, flux
conservation, and approximately second-order spatial convergence. Its full
arrays and report are in `results/stage2-scattering-validation/`.

## Synthetic deterministic benchmark outcomes

All **11** packet validation checks passed. These spectra are mathematical
fixtures with explicitly assigned synthetic factors, not claims about a designed
semiconductor device. Their exact settings and factor formulas are saved in
`results/stage2-validation/manifest.json`, with full spectra in `arrays.npz`.
The base Gaussian has center 20 meV, density width 2 meV, window [2,38] meV,
721 energy nodes, and target factor 1. Ordinary alignment uses [-0.25,+0.25] ps,
201 scan points, and a 1e-7 ps local tolerance.

| Case | Computed transmitted probability | Computed raw fidelity | Computed aligned fidelity | Outcome |
| --- | --- | --- | --- | --- |
| Identical reference | 1.0000000000000002 | 1.0000000000000004 | 1.0000000000000004 | PASS |
| Global phase 1.73 rad | 1.0000000000000002 | 1.0000000000000004 | 1.0000000000000004 | PASS |
| Pure lag +0.12 ps | 1 | 0.8755081677114223 | 1.0000000000000004 | PASS; recovered +0.12 ps |
| Pure lag +0.4 ps, allowed ±0.1 ps | 1 | 0.2282688700864002 | 0.43563850864501114 | PASS; +0.1 ps boundary flagged |
| Quadratic phase, beta=0.08 meV⁻² | 1.0000000000000002 | 0.842271400661512 | 0.842271400661512 | PASS |
| Gaussian amplitude filter, width 1.5 meV | 0.6000000000000001 | 0.8823529411764709 | 0.8823529411764709 | PASS |
| Constant amplitude 1e-7 | 1.0000000000000003e-14 | 1 | 1 | PASS; low throughput flagged |
| Zero amplitude | 0 | undefined | undefined | PASS; no normalized state invented |

The other three checks verify quadrature refinement, the complex analytic
position-space wavefunction with its energy Jacobian, and its spatial norm.
No analytical benchmark failed. Small excursions above one are retained roundoff,
not clipped or reported as improved physical probabilities.

### Energy-quadrature convergence

The deliberately truncated benchmark has center 15 meV, width 4 meV, window
[10,30] meV, unit target, and

\[
t(E)=0.8\exp[-(E-15)^2/(4\cdot5^2)]
\exp\{i[(E-15)0.1/\hbar+0.025(E-15)^2]\}.
\]

Independent adaptive integration (real and imaginary parts separately,
`epsabs=epsrel=1e-12`) gives probability `0.5282710658039789` and raw fidelity
`0.6683205146876013`. The production trapezoidal rule gives:

| Energy nodes | Spacing (meV) | Absolute probability error | Absolute raw-fidelity error |
| --- | --- | --- | --- |
| 41 | 0.5 | 3.5010144605e-5 | 3.5245872862e-5 |
| 81 | 0.25 | 8.7548006059e-6 | 8.8261019375e-6 |
| 161 | 0.125 | 2.1888388040e-6 | 2.2074397080e-6 |
| 321 | 0.0625 | 5.4721832221e-7 | 5.5191705928e-7 |

Maximum-error reduction ratios are 3.99337, 3.99834, and 3.99959. This supports
second-order quadrature convergence for this smooth integrand on the declared
finite interval. It is not a convergence guarantee for arbitrary resonant devices.

### Reconstruction and tolerances

The independent analytic wave-number Gaussian uses k in [0.1,0.5] nm⁻¹ with
2001 nodes, center 0.3 nm⁻¹, width 0.015 nm⁻¹, mass ratio 0.067, discrete spacing
0.5 nm, and time zero. Position samples span [-300,300] nm with 1201 nodes.
The computed maximum complex-wavefunction error is `1.823327183680945e-10`
nm⁻¹ᐟ²; the spatial integral is `0.9999999966666631`.

The 2e-9 wavefunction and 1e-8 spatial-norm regression guards allow margin above
those measured finite-quadrature errors. Separate tests using a Gaussian in
energy check spatial norms at times 0 and 0.25 ps, for amplitudes 1 and 0.25,
including the velocity and probability scaling. Gaussian integral fidelity
checks use 2e-12 in the standalone driver, well above observed near-roundoff
differences; the nine-sigma window makes tail truncation negligible there.
The 6e-7 finest-grid integration guard and [3.9,4.1] reduction-ratio guard are
informed by the convergence table. Delay recovery uses a 3e-7 ps guard relative
to the configured 1e-7 ps local search tolerance. These are numerical regression
choices for these cases, never physical laws or universal device accuracy claims.

## Physical example, exact settings, and plots

The complete configuration is [examples/wavepacket.json](../examples/wavepacket.json),
copied unchanged to [the run's config.json](../results/stage2-packet/config.json).
It specifies mass ratio 0.067, zero-potential leads, a 40 meV rectangular barrier
of width 10 nm centered at zero, domain [-40,40] nm with 801 nodes, and energies
[1,100] meV with 801 nodes. The clean target is explicitly a free channel.
The packet center is 40 meV, density width is 4 meV, and the sweep widths are
[1,2,4,6,8] meV. The source offset is -200 nm from the left reference plane;
the output is displayed at 0.9 ps over a 600 nm right-lead window, with 1201
position samples. Delay bounds are ±0.25 ps, scan count 201, tolerance 1e-7 ps.

The actual command printed:

```text
Phaseward packet saved: /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage2-packet
Transmitted probability: 0.36607298
Reference transmitted probability: 1
Raw conditional fidelity: 0.9863606415434641
Delay-aligned conditional fidelity: 0.9890243192681996
Estimated output lag (ps): 0.008599541991730342 (interior_optimum)
```

The high conditional fidelity coexists with only about 36.6% transmitted
probability. Reflection is `0.6339270178750565`; integrated probability closure
error is `2.0872192862952943e-14`. The largest stationary conservation error is
`9.192646643896296e-14`, and largest scaled residual is `2.2886766763611705e-16`.
The target's probability is `1.0000000000000326` before display rounding.

Using every other energy node changes probability by `1.9984e-15`, raw fidelity
by `5.5511e-16`, aligned fidelity by `2.2204e-16`, and lag by `1.0113e-14` ps.
This smooth example is energy-quadrature converged to roundoff on these grids;
that statement does **not** establish equally small continuum spatial error.
Stationary spatial errors were measured separately in the stage-1 study.

Captured spatial probabilities are `0.9999997915932675` for the incident
left-lead window at time zero, `0.3658880559570361` for the actual outgoing
right-lead window at 0.9 ps, and `0.9995479683097601` for the target at 0.9 ps.
The outgoing finite-window integrals differ from the spectral totals because
the displayed component tails are not all in those windows. They were not
renormalized. Fine/coarse energy-grid density L1 differences in these viewports
are at most `4.9626e-13`; this is a local quadrature comparison, not a claim about
all positions or arbitrarily late times.

Sample figures from those exact settings:

![Incident and outgoing lead components](/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage2-packet/packet_position.png)

![Energy densities and complex phase difference](/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage2-packet/packet_spectra.png)

![Conditional fidelity and throughput versus bandwidth](/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage2-packet/packet_bandwidth.png)

[Bounded delay scan](../results/stage2-packet/packet_delay.png) and
[synthetic convergence and reconstruction checks](../results/stage2-validation/packet_validation.png)
are also saved, with SVG/PDF copies. All five new figure types were visually
inspected for readable labels, units, and conventions. Numerical validation is
independent of visual appearance.

## Artifact audit and remaining scope

All output hashes were recomputed successfully: six demo artifacts, eight
scattering-example artifacts, 22 packet-example artifacts, seven synthetic
packet-study artifacts, and six stationary-study artifacts. Every bundle has a
manifest with the same final code identity. The saved packet configuration equals
the checked-in JSON exactly. `git check-ignore` confirmed that generated results
and `.venv` remain ignored. CSVs, NPZ arrays, JSON settings, and figures must be
kept with their manifests.

There are no unresolved PROMPT 2 blockers. Limits remain explicit: constant mass,
real potentials, two open lead channels, finite energy windows, finite-difference
dispersion, lead-only position reconstruction, and a finite delay scan with local
refinement. Narrow resonances, very large display distances/times, or different
potentials require fresh convergence checks. An overlap lag is not asserted to
be a universal arrival time. Physical disorder, sensitivity, optimization,
robustness claims, and the GUI await subsequent user prompts.
