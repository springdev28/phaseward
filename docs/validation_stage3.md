# PROMPT 3 validation — gates, disorder, and complex sensitivity

Run date: 2026-11-18. Phaseward package/CLI version: **qwave 0.4.0**.
This stage extends the existing stationary solver and packet implementation.
It does not optimize a device, compute a disorder-robust packet fidelity, or
establish a research improvement. All values below come from local Python runs.

## Environment and source identity

The final runs used CPython 3.13.0 on native Apple Silicon (`arm64`, Darwin
25.6.0, 8 logical CPUs), NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, and
pytest 9.2.0. `qwave doctor --dev` reported both runtime and development ready;
`python -m pip check` reported `No broken requirements found.` No network,
GPU, cloud service, external account, or physical device was used by these runs.

The existing environment uses a regular wheel install because its editable
install had a hidden `.pth` problem; see [stage 1](validation_stage1.md).
The final wheel was rebuilt and installed, then all 20 installed Python modules
were compared byte-for-byte against `src/qwave`. Tests and final commands used
the installed package without a `PYTHONPATH` override.

- Source code SHA-256 identity:
  `013500cad3c83d95ec8da9a07ce14e699612e913163d448aee2a3b5b007d09c4`.
- Wheel: `qwave-0.4.0-py3-none-any.whl`, 63,928 bytes, SHA-256
  `5285c498834dc948a939b7ab2d5f31345d69333386c76ca6929c31b3f5322ae9`.
- The repository has no commit to cite. Per-file source hashes and resolved
  configuration, UTC timestamp, seeds, software, and assumptions are in each
  run's manifest. The source audit is in `results/stage3-logs/source-audit.json`.
- Only Python 3.13 was executed here; the declared minimum is Python 3.11.

## Exact final build and validation commands

Working directory for all commands:
`/Users/baharyuksel/Documents/ChatGPT/Phaseward`.
Each output directory below was new. Reruns must choose fresh names. Commands
are grouped as executed; the four independent validation groups ran concurrently.

```sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage3-wheels .
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage3-wheels/qwave-0.4.0-py3-none-any.whl
mkdir -p results/stage3-logs
.venv/bin/qwave --version
.venv/bin/python - <<'PY' > results/stage3-logs/source-audit.json
from pathlib import Path
import json
import qwave
from qwave.provenance import source_identity

installed=Path(qwave.__file__).parent
assert '.venv/lib/' in str(installed), installed
sources=sorted(Path('src/qwave').glob('*.py'))
for path in sources:
    assert path.read_bytes() == (installed/path.name).read_bytes(), path
print(json.dumps({'version':qwave.__version__,'installed_path':str(installed),
                  'matching_python_modules':len(sources),'source':source_identity()},indent=2))
PY
```

```sh
set -o pipefail
source .venv/bin/activate
pytest | tee results/stage3-logs/pytest.txt
```

```sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage3-baseline"
qwave doctor --dev > results/stage3-logs/doctor.json
qwave config-check examples/demo.json > results/stage3-logs/demo-config-check.json
qwave config-check examples/barrier.json > results/stage3-logs/barrier-config-check.json
qwave config-check examples/wavepacket.json > results/stage3-logs/packet-config-check.json
qwave demo --config examples/demo.json --output results/stage3-demo --plot > results/stage3-logs/demo.txt
qwave scatter --config examples/barrier.json --output results/stage3-barrier > results/stage3-logs/scatter.txt
qwave packet --config examples/wavepacket.json --output results/stage3-packet > results/stage3-logs/packet.txt
python -m pip check > results/stage3-logs/pip-check.txt
```

```sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage3-new"
qwave config-check examples/disorder.json > results/stage3-logs/disorder-config-check.json
qwave config-check examples/sensitivity.json > results/stage3-logs/sensitivity-config-check.json
qwave disorder --config examples/disorder.json --output results/stage3-disorder > results/stage3-logs/disorder.txt
qwave sensitivity --config examples/sensitivity.json --output results/stage3-sensitivity > results/stage3-logs/sensitivity.txt
```

```sh
set -e
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/results/.matplotlib-stage3-validation"
python examples/validate_scattering.py --output results/stage3-scattering-validation > results/stage3-logs/scattering-validation.txt
python examples/validate_packets.py --output results/stage3-packet-validation > results/stage3-logs/packet-validation.txt
```

All four groups exited with status 0. Pip emitted a nonblocking warning about
its unwritable user cache; installation succeeded without that cache. The final
development check before wheel installation was also executed:

```sh
PYTHONPATH=src .venv/bin/pytest tests/test_disorder.py tests/test_sensitivity.py tests/test_disorder_workflow.py
```

It reported `45 passed in 22.89s`. Preliminary bundles in
`results/stage3-disorder-development` and `results/stage3-sensitivity-development`
are retained with their original provenance. The final evidence in this report
uses the version-0.4.0 bundles listed below.

## Test output and what was verified

Final installed-package output, retained verbatim in
`results/stage3-logs/pytest.txt`:

```text
============================= test session starts ==============================
platform darwin -- Python 3.13.0, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/baharyuksel/Documents/ChatGPT/Phaseward
configfile: pyproject.toml
testpaths: tests
collected 166 items

tests/test_cli.py .......                                                [  4%]
tests/test_config.py ..........................                          [ 19%]
tests/test_demo.py ...........                                           [ 26%]
tests/test_disorder.py ...............                                   [ 35%]
tests/test_disorder_workflow.py .....................                    [ 48%]
tests/test_packet_workflow.py ..............                             [ 56%]
tests/test_scatter_workflow.py ...................                       [ 68%]
tests/test_scattering.py ......................                          [ 81%]
tests/test_sensitivity.py .........                                      [ 86%]
tests/test_wavepackets.py ......................                         [100%]

============================= 166 passed in 29.13s ==============================
```

The 45 new tests cover individual/summed gate bounds, channel support and custom
shapes; all three kernel formulas and empirical covariance; seed replay and
amplitude scaling; weighted eigenmode orthonormality, covariance reconstruction,
discarded variance and spatial-grid convergence; complex derivatives and Taylor
remainders; strict configuration rejection; CLI execution; and saved data,
figures, source identity, and artifact checksums. The earlier 121 tests also pass.

Independent checks include the discrete free-channel Born derivative
`dt/dV_j = -i t / (2 tau sin(q))`, complex site perturbations at the endpoints
and interior of a Gaussian device with equal and unequal lead velocities, a
symmetry-protected zero derivative, and the identity
`sum(lambda * abs(D)**2) = J C_K J†`. A derivative of a probability or magnitude
cannot pass the free-channel complex-gradient check.

The spatial covariance eigenvalue test uses 41, 81, and 161 nodes on a fixed
20 nm interval, sigma=2 meV, and ell=2 nm. Its refinement-difference ratio is
required to lie in [3.8, 4.2], with the last two spectra agreeing within 0.1%.
This checks the expected second-order spatial quadrature and catches a missing
grid weight. Finite-difference and Taylor tests independently require approximately
fourfold error reduction when halving a step in their perturbative regimes.

Roundoff guards (for example 2e-14 for weighted orthogonality and the analytic
free gradient, and 2e-13 for covariance reconstruction) apply to these small
float64 test problems. Covariance sampling guards use Gaussian standard errors
and expected covariance-error RMS: six standard errors per mean/variance and
four expected RMS units for the matrix error. They are deterministic regression
screens, not simultaneous confidence intervals or universal physical laws.
The example's separate derivative-step study below measures its own error range.

The earlier independent validation scripts also reported every check passing:
9 stationary-scattering checks (including continuum barrier transmission and
complex amplitude, independent Gaussian ODE matching, and grid convergence),
and 11 synthetic packet checks (including global phase, bounded delay, throughput,
quadrature, velocity/Jacobian, and spatial normalization). Their arrays and
thresholds remain in their own stage-3 regression bundles.

## Exact example configuration

The complete machine-readable inputs are [disorder.json](../examples/disorder.json)
and [sensitivity.json](../examples/sensitivity.json), copied without changes into
their result directories as `config.json`.

| Parameter | Value |
| --- | --- |
| Scattering domain/grid | −40 to +40 nm, 401 nodes, dx=0.2 nm |
| Physical channel/grid | −30 to +30 nm, 301 nodes; zero gate/disorder outside |
| Effective mass | 0.067 times free-electron mass, illustrative and configurable |
| Leads/background | Both lead potential energies zero; free zero background |
| Energy samples | 8 to 80 meV, 73 nodes |
| Gates | Four Gaussians at −18, −6, +6, +18 nm, each width sigma=4 nm |
| Gate amplitudes | 8, 15, 12, 6 meV; each allowed within [−30, +30] meV |
| Gate normalization/bounds | Sampled peak absolute value 1; 5 nm smooth edge taper; summed absolute bound 60 meV |
| Disorder | Gaussian covariance, sigma=2 meV, ell=5 nm, no boundary taper |
| Retained modes | K=8; spatial trapezoidal orthonormality |
| Covariance validation | 4096 samples, PCG64 seed 1729 |
| Transport validation | 16 independent samples, PCG64 seed 271828 |
| Coefficient step scan | 1, .3, .1, .03, .01, .003, .001, .0001, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9 meV sqrt(nm) |
| Selected coefficient step | .003 meV sqrt(nm) |
| Disorder scales | 0, .05, .1, .2, .5, 1, 2, 4 times nominal sigma |

No-taper disorder preserves the requested stationary covariance on the closed
channel grid but makes a hard transition to zero outside. This is explicit and
can be changed using `boundary_taper_nm`; tapering changes the target covariance.
The gate bound applies to gates, not to Gaussian disorder or to a hypothetical
electrode voltage. The complex-t phase planes remain the solver's endpoint
planes and are identical across all perturbed solves.

## Covariance and KL results

The convention is `Phi.T W Phi = I`, `Var(eta_k)=lambda_k`, and
`deltaV=Phi eta`, with `eta=sqrt(lambda)*z` and independent standard-normal `z`.
Phi has units nm^(-1/2), lambda meV² nm, and eta meV sqrt(nm). No second factor
of sqrt(lambda), sample-wise normalization, or spatial demeaning is applied.
See [the full derivation](disorder.md).

| Measured diagnostic | Final value |
| --- | ---: |
| Total integrated disorder variance | 240.0 meV² nm |
| Eight-mode integrated variance | 227.9621605588 meV² nm |
| Retained fraction | 0.9498423357 |
| Weighted orthonormality max error | 2.3315e-15 |
| Full covariance relative Frobenius reconstruction error | 1.9659e-15 |
| Full-sample mean empirical/target variance ratio | 1.005033738 |
| KL-sample mean empirical/KL-target variance ratio | 1.004992013 |
| Largest full-sample variance error in standard errors | 1.4778 |
| Full covariance error / expected sampling RMS | 0.86572 |
| Target correlation at 5 nm / empirical | 0.606530660 / 0.605840900 |
| KL target correlation at 5 nm / empirical | 0.674128810 / 0.673441418 |

The full and retained covariance sampling screens passed. Retaining 94.98% of
integrated variance does **not** preserve every correlation: the correlation
at 5 nm changes after truncation, as the paired values show. This difference is
reported rather than removed by rescaling. Observed mean discarded spatial
squared norm was 12.1167710558 meV² nm; its expected value is the discarded sum
of eigenvalues, not a prescribed sample-by-sample norm.

The covariance has numerical resolved rank 33 at the recorded threshold
2.084219254e-10 meV² nm. The minimum computed eigenvalue was −1.2520e-14;
134 small negative eigenvalues were clipped, with total clipped mass
2.1089e-13 meV² nm. The full reconstruction error above records the effect.
No diagonal jitter was added. The eigenvalue figure preserves positive values
below the resolution threshold; that tiny tail is roundoff-level and must not
be interpreted as resolved physical modes.

## Derivative convergence and first-order validity

The baseline preserves complex t. Centered differences are compared with an
independently implemented implicit derivative of the same discrete equations,
then also checked by the independent analytic free-channel tests. Agreement
between two implementations of the discrete model is not proof that the
continuum approximation is accurate for an arbitrary new grid or device.

| Coefficient step (meV sqrt(nm)) | Maximum absolute complex derivative error (1/(meV sqrt(nm))) |
| ---: | ---: |
| 1 | 2.3226e-4 |
| .1 | 2.3286e-6 |
| .01 | 2.3287e-8 |
| .003 (selected) | 2.0757e-9 |
| .001 | 2.5939e-10 |
| .0001 | 9.0415e-10 |
| 1e-6 | 8.1886e-8 |
| 1e-9 | 1.1243e-4 |

The large-step error follows second-order convergence; smaller is eventually
worse. All eight modes show small-step error growth. The best tested step is
.001 for modes 1–5 and .003 for modes 6–8. The declared common step .003 is used
for the full-solve comparison; it is not silently replaced with fitted per-mode
steps. Its derivative error is much smaller than the observed Taylor remainders.

Every tested potential direction passed the 1% representation-error screen;
even at 1e-9 the worst direction error was 5.0768e-6. Thus solver/subtraction
roundoff becomes important before potential changes disappear. The last-step
subtraction-only estimate, 2.2204e-7, is smaller than the observed 1.1243e-4:
it is not a forward-error bound for the linear solve. Separate tests deliberately
use an unrepresentable step and verify that it is flagged. Reassembled baseline
t differed by at most 2.6679e-14; the implicit-response scaled residual was
1.5048e-16.

Errors below average squared complex-amplitude errors over the 16 paired
realizations and the energy interval with normalized trapezoidal weights, then
take the square root. Taylor error compares the linear prediction with the
full **K-mode** solve. KL error compares the paired full-K and full-covariance
solves. The two RMS errors must not be added as if statistically independent.
The combined error is measured directly and saved separately.

| Nominal scaled sigma (meV) | Taylor RMS error | KL truncation RMS error | Taylor error / RMS full K-mode change |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | undefined |
| .1 | 2.4545e-4 | 3.1097e-4 | .02428 |
| .2 | 9.7864e-4 | 6.1987e-4 | .04847 |
| .4 | .00388382 | .00123172 | .09652 |
| 1 | .0234652 | .00302710 | .23654 |
| 2 | .0863471 | .00594250 | .44827 |
| 4 | .279516 | .0117436 | .77637 |
| 8 | .745036 | .0243738 | 1.19740 |

The small-disorder Taylor remainder initially grows approximately quadratically.
At the nominal 2 meV disorder it is already about 45% of the actual complex
change, and at 8 meV it exceeds that change. First-order theory is inadequate
there for an accurate prediction in this example. These are fixed-grid,
fixed-energy-window results from 16 realizations, not a universal threshold.
Mode truncation also contributes error even when Taylor error is small.

Some linearized squared amplitudes exceed one: 10 of 1168 energy/realization
values even at nominal 0.1 meV, increasing to 1008 at 8 meV (threshold 1+1e-10).
A first-order amplitude alone does not enforce probability conservation; these
values are preserved and reported. They are not used as physical probabilities
or called fidelities. The actual nonlinear full solves remained lossless to a
maximum measured `abs(T+R-1)` of **6.6613e-14**, below the configured 1e-8
conservation screen. No full-solve conservation or analytical benchmark failed.

## Saved artifacts, figures, and remaining limits

| Bundle under `results/` | Hashed artifacts, excluding manifest |
| --- | ---: |
| `stage3-demo` | 6 |
| `stage3-barrier` | 8 |
| `stage3-packet` | 22 |
| `stage3-disorder` | 21 |
| `stage3-sensitivity` | 26 |
| `stage3-scattering-validation` | 6 |
| `stage3-packet-validation` | 7 |

Every artifact hash in these seven final bundles was recomputed and matched;
every bundle records the installed source identity above. The two new saved
configs match their example files exactly. JSON/CSV/NPZ include numerical arrays,
complex derivatives and amplitudes, full and retained eigenmodes, seeds and raw
normal draws, paired full/retained potential samples, and per-realization errors.
PNG, SVG, and PDF figures accompany them. Result directories and `.venv` remain
Git-ignored; the manifest is written last as the completion marker.

Inspect these generated figures with their exact configs above:

- [Each gate contribution and sum](../results/stage3-disorder/gates.png).
- [Eigenvalue decay, retained fraction, modes, and local variance](../results/stage3-disorder/covariance_modes.png).
- [Paired full and truncated disorder samples](../results/stage3-disorder/disorder_samples.png).
- [Empirical covariance, variance, and correlation](../results/stage3-disorder/covariance_validation.png).
- [Sensitivity versus position/mode/energy](../results/stage3-sensitivity/sensitivity_maps.png).
- [Complex derivative step convergence](../results/stage3-sensitivity/derivative_convergence.png).
- [Taylor and mode-truncation errors versus disorder](../results/stage3-sensitivity/linearization_error.png).

There are no unresolved execution blockers. The measured limitations are finite
grid and energy resolution, finite ensemble size, omitted KL modes, roundoff at
small derivative steps, and breakdown of the first-order approximation at larger
disorder. The inherited constant-mass coherent one-dimensional model still omits
contacts, decoherence, many-electron effects, and an electrode electrostatic model.
The new commands impose documented CPU/memory limits (including at most 801
channel covariance nodes); these are engineering limits, not physical laws.
Optimization, training/held-out evaluation, and a GUI await later prompts.

The equations and conventions are derived in [disorder.md](disorder.md) and
[sensitivity.md](sensitivity.md); [architecture.md](architecture.md) gives the
updated module map and file tree.
