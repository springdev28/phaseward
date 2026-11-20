# Phaseward scientific and software audit

**Audited 2026-11-20, qwave 0.9.0.** The executed local workflows pass their
implemented checks. This is a bounded verification record, not certification of
all supported inputs or proof that the proposed method is superior. In fact,
the benchmark comparisons **contradict** a sensitivity-method advantage over
the clean and Monte Carlo baselines for the declared loss. Unfavorable results,
infeasible fixed designs, numerical noise and exhausted searches are retained.

## Scope and changes

The audit covers the installed package, strict configurations, constants/units,
potential sampling, stationary solver and references, spectral packets,
gates/covariance, sensitivity, constrained optimization and caching, experiment
ordering/statistics/provenance, plotting, CLI, GUI workers/result browsing,
executable teaching material and frozen-run manuscript export. Existing tests
were examined for shared implementations; passing a self-consistency test was
not treated as independent validation.

Two substantive optimization rejection gaps were reproduced before repair:

1. Conservation alone allowed a response with a NaN derivative, a deliberately
   bad response/forward residual, or a mismatched reassembled complex amplitude
   into the cache/evaluator. Four fault-injection regression cases failed in
   0.8.0. The cache now checks finite data, forward residuals, response shape and
   residuals, and complex-amplitude consistency before insertion. Nonfinite
   objective/constraint values cannot be selected. Failed work remains charged.
2. Complex gate inputs were cast to real with a NumPy warning. They now raise an
   explicit validation error before work is charged. The regression initially
   failed, then passed after repair.

The actual browser smoke test also found a hard-coded `localhost:8501` footer
when launching on port 8503. It now displays the configured port. Version 0.9.0
was rebuilt/reinstalled, and 52 package/data files matched the workspace before
the final full test run. No scientific model, objective, seed distribution,
comparison budget, output score or expected improvement was changed.

The first acceptance driver incorrectly sent `examples/gui_preview.json` to
the CLI config checker. That file is a GUI request wrapper, as documented; the
correct GUI validator passed. The corrected acceptance run validates all 13 CLI
JSON examples plus that GUI request. The initial stopped run and its logs remain
in `results/stage9-audit-logs`. The first sandboxed server launch could not bind
a socket; an authorized localhost-only retry succeeded. These were execution
issues, not failed physics benchmarks.

## Independent numerical evidence

The new [reference implementations](../examples/independent_transport_oracles.py)
import **no qwave code**. They use independently written SI conversions,
two-by-two lattice recurrence matching, four-by-four continuum matching, an
exact impurity identity and closed spectral integrals. The recurrence reference
rejects ill-conditioned systems and is not an opaque-barrier production solver.
The [executable audit](../examples/audit_numerics.py) records exact arrays,
criteria, versions, units and audit seeds. Its [22 checks](../results/stage9-independent/checks.csv)
all passed.

| Claim checked | Independent evidence | Measured result |
|---|---|---|
| Flux normalization and phase | Two-sided unitary S, unequal open lead potentials; full complex reciprocity | max `|S†S−I|` 1.15e−14; reciprocity error 6.68e−15 |
| Solver assembly | Separate recurrence boundary solve | max complex t/r difference 2.11e−13 |
| Reference planes | Shift a compact potential by five nodes | t invariant and r acquires `exp(2ik displacement)`; error 2.84e−15 |
| Forbidden energies | Negative, zero, upper edge and above-band attempts | All rejected; existing tests also cover unequal closed leads and edge guards |
| Continuum rectangular barrier | Continuity and derivative matching below, at and above barrier height | t/r error 0.00442 → 6.90e−5 as spacing 0.25 → 0.03125 nm; orders 2.0010, 2.0003, 2.0001 |
| Complex derivative at nonzero potential | Exact lattice impurity t/r and `dt/dU` | max amplitude error 3.38e−15; derivative error 2.34e−17 meV⁻¹ |
| Perturbation calculus | Analytic impurity derivative vs centered differences and full perturbed solves | best tested derivative error 9.61e−11; small Taylor remainder orders 1.999, 1.998, 1.995 |
| Covariance normalization/statistics | Separate Cholesky sampler; Gaussian chi-square/Wishart sampling laws; projection into weighted KL modes | No marginal variance interval violations; maximum covariance entry error 2.99 standard errors |
| Packet P, F, lag and conjugation | Closed integrals for a uniform energy spectrum with exponential attenuation and linear phase | Finest max P/F error 1.67e−6; order ≈2; lag error 1.25e−11 ps |
| Feasibility | Independent recurrence amplitudes plus SciPy quadrature and physical bounds | Feasible and infeasible gate vectors correctly distinguished; opaque physical impurity remains low-throughput despite F >0.999 |

All numerical tolerances are regression guards, **not physical laws**. For
well-conditioned discrete identity checks the guards are above measured roundoff;
continuum and quadrature guards accompany observed second-order refinement.
Covariance variance intervals use the exact marginal chi-square law with
Bonferroni family alpha 0.001. The six-standard-error covariance-entry diagnostic
is conservative, not an exact simultaneous confidence region. Both samplers
use 6,000 draws with fixed audit-only seeds 935001/935002. Covariance shapes
remain weighted-orthonormal; eigenvalues are coefficient variances, not a second
factor inside the shapes.

The deliberately tiny derivative step `1e-12 meV sqrt(nm)` has error 5.20e−4,
much worse than the `0.01` step. This exposes subtraction/representation noise;
it is retained in the figure rather than hidden. The synthetic packet's exact
P, raw F and aligned F are 0.58233816, 0.38830868 and 0.97104204. Alignment does
not repair its amplitude distortion. These are mathematical benchmarks, not
device discoveries.

The existing independently derived scattering and packet validators were also
rerun. Free propagation, rectangular barriers, Gaussian-barrier DOP853 matching,
ODE tolerance tightening, conservation, exact Gaussian packet identities,
bounded delays, global phase, amplitude filtering, zero/tiny throughput,
quadrature refinement, Jacobian and spatial norm checks passed. The Gaussian
ODE changes by 1.27e−11 when its tolerance is tightened. The packet analytic
position-amplitude error is 1.82e−10 nm⁻¹/² and its finite-window probability is
0.9999999967. Full details: [scattering report](../results/stage9-scattering-validation/report.json),
[packet report](../results/stage9-packet-validation/report.json).

Conservation does not imply continuum accuracy. For example, the free-channel
test at 1 nm spacing has complex continuum-amplitude error 0.1785 while its
conservation error is 4.44e−15. Refinement resolves the discrete-dispersion bias;
a larger disorder sample count cannot fix it.

## Executed software and workflow checks

Final full suite, using the installed wheel without `PYTHONPATH`:

```text
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 82%]
.............................................                            [100%]
261 passed in 115.37s (0:01:55)
```

This includes the real Streamlit AppTest/worker/integration tests (no GUI skips),
all three optimized methods' held-out-seed invariance tests, freeze-before-draw
instrumentation, budget/failure cases, export replay/tampering tests and the new
independent scientific checks. `pip check`, `compileall`, `qwave doctor --dev`,
all supported example config validators, a fresh demo, scatter, packet, disorder,
sensitivity and full `optimize.json` run passed. No linter or static type checker
is configured; byte compilation is a syntax check, not type verification.

Four teaching notebooks executed locally. The structural consistency checker
verified 207 math expressions, 33 equation anchors, 20 mapped functions, 40
mapped tests and 163 inventory hashes. This is not a symbolic proof. A fresh
paper export from this audit's benchmark passed semantic/figure replay and its
standalone verifier checked 69 files and the original-run binding. The paper
Results section remains unfilled. LaTeX compilation was not repeated in this
audit; its prior executed validation is in [stage 8](validation_stage8.md).

Environment: native arm64, eight logical CPUs, macOS Darwin 25.6.0, CPython
3.13.0, NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, pytest 9.2.0 and Streamlit
1.67.0. Dependencies were reused locally. Search/testing commands cap BLAS/OpenMP
threads at one and record that choice. The Git repository has no initial commit;
source hashes identify the tested code, and manifests explicitly record the
missing commit. No commit was fabricated.

The real server ran on `127.0.0.1:8503` with telemetry disabled. All four views
rendered, a wave/packet preview finished, and the saved benchmark opened read-only.
The final browser console had zero errors/warnings; captured requests were to
loopback. The audit server was stopped afterwards. Evidence: [wave screenshot](../results/stage9-final-logs/gui-wave.png),
[saved benchmark screenshot](../results/stage9-final-logs/gui-saved-benchmark.png),
[server log](../results/stage9-final-logs/streamlit-server.txt),
[network capture](../results/stage9-final-logs/browser-network.txt).

## Measured experiments, fairness and limits of inference

| Executed preset | Search cap per B/C/D | Train / validation / held-out draws | Local wall time | Workflow status |
|---|---:|---:|---:|---|
| Laptop smoke | 90 RHS-equivalent sweeps | 2 / 4 / 8 | 6.36 s | completed |
| Laptop benchmark | 240 | 4 / 12 / 32 | 10.26 s | completed |
| Laptop optimization comparison, two P floors | 240 per floor | 4 / 12 / 32, paired across floors | 14.68 s | completed |
| Research benchmark, three starts | 600 | 8 / 32 / 128 | 23.48 s | completed |

The research preset was run unchanged after measuring the laptop runtime. It
is one predefined profile, not a newly tuned test distribution. All evaluation
solves, preflight/postflight checks and required optimized feasibility checks
passed. The source preserves two starts for laptop B/C/D and three for research,
identical gate counts/bounds/targets and equal maximum search-work caps within
each case. Actual search cost differs: in the laptop two-floor comparison B/C/D
consume 240/240/189 sweeps per floor. B and C hit their work caps; D terminates
successfully. A is a fixed comparison with one solve, not an optimized competitor
given a hidden search budget. Preflight, postflight and evaluation costs remain
separate. These are finite-budget comparisons, not proofs of global optimality.

Training, validation, held-out, initialization, convergence and bootstrap roots
and child seeds were checked for role overlap. Search code receives training
potentials only. Instrumented tests check that all designs across cases freeze
before validation or held-out draws exist. Replacing evaluation seeds leaves
every B/C/D search candidate/objective/residual unchanged. Pairing deliberately
reuses a held-out draw across methods/floors. Neither this nor replaying a preset
creates independent optimization replications.

The laptop benchmark was repeated. **264 numerical arrays are exactly identical**,
including model, scattering, seed, sensitivity and non-timing bootstrap data;
frozen candidates are identical. Six bootstrap arrays for measured solver time
were correctly excluded from deterministic equality, as were provenance timestamps.
The data audit checks 17 bundles, 292 output hashes and 2,298 finite floating/
complex arrays. Across five suite executions, 1,520 trial rows pass probability/
fidelity range checks; that count includes the deterministic replay and is not
a claim of 1,520 independent observations. See [machine-readable audit](../results/stage9-final-logs/data_audit.json).

The primary measured loss is `0.5*(1−P) + 0.5*(1−F_raw)`. Positive D-minus-baseline
means worse loss. Laptop benchmark paired, family-adjusted basic-bootstrap
intervals are:

| D minus comparison | Mean loss difference | Family interval | Recorded classification |
|---|---:|---|---|
| A fixed | −0.00712558 | [−0.00884151, −0.00507621] | supports |
| B clean | +0.01691146 | [+0.01627027, +0.01766247] | contradicts |
| C Monte Carlo | +0.01524967 | [+0.01471459, +0.01586540] | contradicts |

The research benchmark likewise contradicts improvement over B/C: D-minus-B
is +0.01635706, interval [+0.01602168,+0.01670223]; D-minus-C is +0.01615427,
interval [+0.01581264,+0.01650581]. All findings are conditional on the fixed
model, target, weighting, finite search budget and sampled retained-KL disorder.
They are not publication-ready general claims or hardware validation.

At the stricter 0.98 clean-throughput floor, A has P=0.96735 and is explicitly
infeasible. It remains visible in plots/data, but the corresponding primary
comparison is marked unresolved/ineligible. B/C/D retain useful throughput;
D does not obtain its objective value by switching transport off. Its raw
fidelity is lower than the other optimized baselines, with a substantial delay
component. Aligned fidelity is kept as a separately labeled secondary metric.

Every frozen laptop design was independently rechecked with recurrence
amplitudes and quadrature (largest P/F discrepancy 1.41e−14). Separate spatial
refinement 161→321→641 and energy refinement 57→113→225 preserved all feasibility
classifications, including A's failure at the strict floor. The largest coarse
to finest clean P/F shift is about 1.56e−4 (D raw fidelity); this is numerical
bias, not a physical effect. The research designs also passed independent
coarse-grid metric checks (max discrepancy 5.02e−14) and clean refinements
201→401→801 / 81→161→321. No gate vector was changed or reselected. These clean
checks do not certify the full disordered evaluation ensemble.

## Plot and boundary inspection

The [scattering plot](../results/stage9-scatter/scattering.png) labels nm/meV,
unit-flux probabilities, radians and the actual phase planes. T/R bounds and
conservation are checked numerically, not judged only by the picture. The
[packet position plot](../results/stage9-packet/packet_position.png) labels
unconditional probability density in nm⁻¹, separate incoming/outgoing times,
P and conditional F; it implies no classical trajectory.

For that packet, P=0.3660729821, raw F=0.9863606415, aligned F=0.9890243193 and
lag=0.008599542 ps with an interior optimum. Its incoming window contains
0.999999792 probability; outgoing contains 0.365888056 rather than all of P.
Finite tails outside the display explain the difference. Coarse/fine density
L1 differences are ≤4.97e−13 for this example; the plot is not display-renormalized.

The [sensitivity plot](../results/stage9-sensitivity/linearization_error.png)
retains the large-disorder breakdown: Taylor error divided by the actual change
exceeds one at the largest tested strength. KL truncation and Taylor error are
separate curves. The [independent audit plot](../results/stage9-independent/independent_checks.png)
shows cancellation at tiny steps, second-order refinement and statistical
variance fluctuations. The [held-out distributions](../results/stage9-optimization-comparison/distributions_declared_device_1.png)
show all methods, with the infeasible fixed baseline labeled. Axes, legends and
underlying arrays were inspected; no plotted improvement was fabricated.

Default disorder uses a hard channel cutoff unless a taper is specified. That
is a declared boundary model, not a numerical absorber. It can create scattering
at channel edges. The benchmark retains about 86.24% of the full integrated
covariance variance in six modes. Increasing random sample count cannot recover
discarded modes or remove the discrete-dispersion bias.

## Known limitations and next experiment

- Only this Apple Silicon/Python/dependency combination was executed. Supported
  Python/package ranges are not a tested matrix. The regular wheel works; a
  fresh editable install was not re-proven after the earlier `.pth` issue.
- The benchmark research profile ran; other research-profile variants,
  exhaustive parameter sweeps and independent optimization replications did not.
  Passing the suite's convergence diagnostics does not certify every user device.
- The physical model excludes variable mass, interactions, decoherence,
  contacts, calibrated electrostatics and hardware. Closed-channel multichannel
  extensions are unsupported, not silently approximated.
- Dense covariance has an 801-node channel guard and numerical-rank limits.
  Grid-dependent gate peak normalization and hard disorder cutoffs need explicit
  attention when refining or changing a model.
- Lead packet reconstructions are asymptotic components. Extreme windows/times
  can alias a finite energy grid; coarse/fine and window diagnostics must be
  reviewed. They are not the full evolving state inside the device.
- Local SLSQP and common finite work caps do not equalize wall-clock time or
  guarantee optimality. Several searches stop at their caps; failure records
  remain evidence. The sensitivity objective is a surrogate, not fidelity,
  failure probability or a guarantee of useful robustness.
- No numerical failure was left unexplained in the executed acceptance runs.
  This does not establish absence of defects. Unsigned hashes and an uncommitted
  working tree are weaker provenance than a reviewed source checkpoint.

**Recommended next scientific experiment:** preregister a surrogate-validity
study before drawing new final seeds. Keep the same model, target and fairness
rules; use independent optimization replications and a prespecified small-to-
moderate sigma sweep. Separate clean target mismatch/delay from disorder-induced
degradation, and test whether J predicts the weighted complex-amplitude change
it actually approximates. Evaluate full covariance or a prespecified ≥99%
retained-variance representation, with fixed-field grid refinement. Set the
numerical error allowance below a declared fraction of the minimum meaningful
effect, then choose held-out sample count using development-only variability.
Report P, raw F, aligned F and delays separately; keep the existing declared loss
as the primary comparison unless a new protocol explicitly changes it. If the
surrogate fails even in its perturbative regime, investigate the mathematics;
if it predicts amplitude variance but not packet loss, report that limitation
instead of forcing a favorable optimization result.

## Exact commands and evidence

The [acceptance driver](../results/stage9-final-logs/acceptance.py),
[supplemental frozen audit](../results/stage9-final-logs/supplemental.py),
[research command](../results/stage9-final-logs/research_validation.py) and
[final data checks](../results/stage9-final-logs/final_data_checks.py) record
argument vectors without shell interpolation. [executed_commands.json](../results/stage9-final-logs/executed_commands.json)
contains working directories, environment overrides, exit codes and elapsed
times. Matching stdout/stderr files preserve actual test and CLI output.
The scripts use fresh output folders; rerunning them unchanged would correctly
reject existing scientific results. Use new names from [HOW_TO_RUN.md](../HOW_TO_RUN.md).

The following command table is generated from that execution record, not a plan.

| Command | Exit | Seconds | Saved stdout |
|---|---:|---:|---|
| wheel | 0 | 1.20 | [output](../results/stage9-final-logs/wheel.stdout.txt) |
| install | 0 | 0.46 | [output](../results/stage9-final-logs/install.stdout.txt) |
| source-match | 0 | 0.04 | [output](../results/stage9-final-logs/source-match.stdout.txt) |
| pip-check | 0 | 0.24 | [output](../results/stage9-final-logs/pip-check.stdout.txt) |
| compileall | 0 | 0.05 | [output](../results/stage9-final-logs/compileall.stdout.txt) |
| pytest | 0 | 116.02 | [output](../results/stage9-final-logs/pytest.stdout.txt) |
| doctor | 0 | 0.69 | [output](../results/stage9-final-logs/doctor.stdout.txt) |
| config-barrier | 0 | 0.41 | [output](../results/stage9-final-logs/config-barrier.stdout.txt) |
| config-demo | 0 | 0.39 | [output](../results/stage9-final-logs/config-demo.stdout.txt) |
| config-disorder | 0 | 0.39 | [output](../results/stage9-final-logs/config-disorder.stdout.txt) |
| config-experiment_benchmark | 0 | 0.41 | [output](../results/stage9-final-logs/config-experiment_benchmark.stdout.txt) |
| config-experiment_convergence_study | 0 | 0.43 | [output](../results/stage9-final-logs/config-experiment_convergence_study.stdout.txt) |
| config-experiment_disorder_sweep | 0 | 0.42 | [output](../results/stage9-final-logs/config-experiment_disorder_sweep.stdout.txt) |
| config-experiment_optimization_comparison | 0 | 0.41 | [output](../results/stage9-final-logs/config-experiment_optimization_comparison.stdout.txt) |
| config-experiment_research | 0 | 0.41 | [output](../results/stage9-final-logs/config-experiment_research.stdout.txt) |
| config-experiment_smoke | 0 | 0.42 | [output](../results/stage9-final-logs/config-experiment_smoke.stdout.txt) |
| config-optimize | 0 | 0.40 | [output](../results/stage9-final-logs/config-optimize.stdout.txt) |
| config-optimize_quick | 0 | 0.48 | [output](../results/stage9-final-logs/config-optimize_quick.stdout.txt) |
| config-sensitivity | 0 | 0.44 | [output](../results/stage9-final-logs/config-sensitivity.stdout.txt) |
| config-wavepacket | 0 | 0.46 | [output](../results/stage9-final-logs/config-wavepacket.stdout.txt) |
| gui-request-check | 0 | 0.42 | [output](../results/stage9-final-logs/gui-request-check.stdout.txt) |
| quickstart | 0 | 15.51 | [output](../results/stage9-final-logs/quickstart.stdout.txt) |
| scatter | 0 | 1.58 | [output](../results/stage9-final-logs/scatter.stdout.txt) |
| packet | 0 | 2.13 | [output](../results/stage9-final-logs/packet.stdout.txt) |
| disorder | 0 | 4.34 | [output](../results/stage9-final-logs/disorder.stdout.txt) |
| sensitivity | 0 | 8.00 | [output](../results/stage9-final-logs/sensitivity.stdout.txt) |
| optimize | 0 | 12.66 | [output](../results/stage9-final-logs/optimize.stdout.txt) |
| scattering-benchmarks | 0 | 1.72 | [output](../results/stage9-final-logs/scattering-benchmarks.stdout.txt) |
| packet-benchmarks | 0 | 1.48 | [output](../results/stage9-final-logs/packet-benchmarks.stdout.txt) |
| independent-numerics | 0 | 2.79 | [output](../results/stage9-final-logs/independent-numerics.stdout.txt) |
| experiment-smoke | 0 | 6.36 | [output](../results/stage9-final-logs/experiment-smoke.stdout.txt) |
| experiment-benchmark | 0 | 10.26 | [output](../results/stage9-final-logs/experiment-benchmark.stdout.txt) |
| experiment-optimization-comparison | 0 | 14.68 | [output](../results/stage9-final-logs/experiment-optimization-comparison.stdout.txt) |
| benchmark-repeat | 0 | 9.40 | [output](../results/stage9-final-logs/benchmark-repeat.stdout.txt) |
| notebooks | 0 | 8.40 | [output](../results/stage9-final-logs/notebooks.stdout.txt) |
| derivation-consistency | 0 | 0.72 | [output](../results/stage9-final-logs/derivation-consistency.stdout.txt) |
| paper-export | 0 | 5.86 | [output](../results/stage9-final-logs/paper-export.stdout.txt) |
| paper-verify | 0 | 0.04 | [output](../results/stage9-final-logs/paper-verify.stdout.txt) |
| frozen-clean-refinement | 0 | 2.87 | [output](../results/stage9-final-logs/frozen-clean-refinement.stdout.txt) |
| research-benchmark | 0 | 23.48 | [output](../results/stage9-final-logs/research-benchmark.stdout.txt) |
| research-frozen-clean-refinement | 0 | 2.49 | [output](../results/stage9-final-logs/research-frozen-clean-refinement.stdout.txt) |
| data-audit | 0 | 0.62 | [output](../results/stage9-final-logs/data-audit.stdout.txt) |
| added-example-compile | 0 | 0.04 | [output](../results/stage9-final-logs/added-example-compile.stdout.txt) |

<details>
<summary>Exact command lines, including the installed-source comparison</summary>

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage9-final-wheels .
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage9-final-wheels/qwave-0.9.0-py3-none-any.whl
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -c 'from pathlib import Path
import qwave, hashlib, json
source=Path('"'"'src/qwave'"'"'); installed=Path(qwave.__file__).parent
paths=sorted(source.glob('"'"'*.py'"'"'))+[source/'"'"'py.typed'"'"']
paths += [p for p in (source/'"'"'paper_assets'"'"').rglob('"'"'*'"'"') if p.is_file() and p.suffix in {'"'"'.py'"'"','"'"'.md'"'"','"'"'.json'"'"','"'"'.csv'"'"','"'"'.bib'"'"','"'"'.tex'"'"'}]
assert {p.name for p in source.glob('"'"'*.py'"'"')} == {p.name for p in installed.glob('"'"'*.py'"'"')}
assert all(p.read_bytes()==(installed/p.relative_to(source)).read_bytes() for p in paths)
print(json.dumps(dict(package=str(installed),version=qwave.__version__,matched_files=len(paths),files={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}),indent=2))
'
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m pip check
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m compileall -q src/qwave examples tests app.py docs/derivations
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m pytest -q
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave doctor --dev
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/barrier.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/demo.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/disorder.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/experiment_benchmark.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/experiment_convergence_study.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/experiment_disorder_sweep.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/experiment_optimization_comparison.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/experiment_research.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/experiment_smoke.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/optimize.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/optimize_quick.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/sensitivity.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/wavepacket.json
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -c 'import json; from qwave.gui_worker import validate_request; validate_request(json.load(open('"'"'examples/gui_preview.json'"'"'))); print('"'"'GUI request valid'"'"')'
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave demo --config examples/demo.json --output results/stage9-demo --plot
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave scatter --config examples/barrier.json --output results/stage9-scatter
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave packet --config examples/wavepacket.json --output results/stage9-packet
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave disorder --config examples/disorder.json --output results/stage9-disorder
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave sensitivity --config examples/sensitivity.json --output results/stage9-sensitivity
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave optimize --config examples/optimize.json --output results/stage9-optimize
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python examples/validate_scattering.py --output results/stage9-scattering-validation
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python examples/validate_packets.py --output results/stage9-packet-validation
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python examples/audit_numerics.py --output results/stage9-independent
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave experiment smoke --output results/stage9-smoke
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave experiment benchmark --output results/stage9-benchmark
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave experiment optimization-comparison --output results/stage9-optimization-comparison
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave experiment benchmark --output results/stage9-benchmark-repeat
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python docs/derivations/run_notebooks.py --output results/stage9-learning
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python docs/derivations/check_package.py --results results/stage9-learning
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave paper-export --run results/stage9-benchmark --output results/stage9-paper
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python results/stage9-paper/verify_package.py
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python examples/audit_frozen_run.py --run results/stage9-optimization-comparison --output results/stage9-frozen-audit
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave experiment benchmark --research --output results/stage9-research-benchmark
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python examples/audit_frozen_run.py --run results/stage9-research-benchmark --output results/stage9-research-frozen-audit
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python results/stage9-final-logs/check_outputs.py
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m compileall -q examples/audit_frozen_run.py
```

Environment overrides for these commands: `MPLCONFIGDIR=results/stage9-final-logs/mpl-cache` (absolute in the record), `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`; `PYTHONPATH` removed.
</details>

The separate browser launch command was:

```sh
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503 --browser.gatherUsageStats false
```

Its output was redirected to the recorded server log; it was stopped with Ctrl+C after the browser checks.
