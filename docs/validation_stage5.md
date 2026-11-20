# PROMPT 5 validation — 2026-11-20

Phaseward/qwave 0.6.0 was built and installed locally. No physics solver, optimizer objective, test distribution or seed partition was changed in response to held-out results. The implementation added a suite layer, paired statistics, convergence diagnostics and reports.

## Environment and source identity

Installed package: /Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/lib/python3.13/site-packages/qwave. All 30 Python/package marker files were compared byte for byte with src/qwave before testing.

Installed source SHA-256: 0e1e0f035eb16c75c43329edcafd021ac98d4bf94cada11ac33d3117977a2a91.

Final wheel: results/stage5-final-wheels/qwave-0.6.0-py3-none-any.whl. The existing environment uses a regular wheel because of the previously documented editable-install issue; the README retains the normal fresh-environment editable quickstart.

Hardware: {"execution_backend": "CPU", "logical_cpu_count": 8, "machine": "arm64", "native_apple_silicon_process": true, "operating_system": "Darwin", "os_release": "25.6.0", "pointer_bits": 64, "processor": "arm", "python_executable": "/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python", "python_implementation": "CPython"}.

Versions: {"matplotlib": "3.11.2", "numpy": "2.5.5", "pip": "24.2", "pytest": "9.2.0", "python": "3.13.0", "qwave": "0.6.0", "qwave_source": "0.6.0", "scipy": "1.18.1", "setuptools": null}.

Git: {"available": true, "commit": null, "scope": "invocation directory; installed code is identified separately by source hashes", "working_tree_dirty": true}. No commit was invented; the workspace is still uncommitted. Source hashes identify the installed code.

## Tests and actual commands

~~~text
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
210 passed in 33.80s
~~~

The 19 new tests include paired-basic-bootstrap agreement with SciPy, reproducible seed prefixes, root/child overlap rejection, exact KL scaling, strict examples, research/overwrite guards, global freeze ordering across two cases, bounded delay and raw trial checks, output hashes, and retained infeasibility/interruption records. The full suite also exercises the earlier analytical scattering, packet, covariance, derivative and optimizer checks.

Build/install and source verification:

~~~sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage5-final-wheels .
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage5-final-wheels/qwave-0.6.0-py3-none-any.whl
MPLCONFIGDIR="$PWD/results/.matplotlib-stage5" .venv/bin/pytest -q > results/stage5-final-logs/pytest.txt 2>&1
.venv/bin/python -u results/stage5-final-logs/acceptance.py
~~~

The acceptance script executed these exact argument lists sequentially, with MPLCONFIGDIR set to the local results/.matplotlib-stage5 directory. Each command below returned 0:

~~~sh
.venv/bin/qwave doctor --dev
.venv/bin/python -m pip check
.venv/bin/qwave config-check examples/demo.json
.venv/bin/qwave config-check examples/optimize.json
.venv/bin/qwave config-check examples/optimize_quick.json
.venv/bin/qwave config-check examples/experiment_smoke.json
.venv/bin/qwave config-check examples/experiment_benchmark.json
.venv/bin/qwave config-check examples/experiment_disorder_sweep.json
.venv/bin/qwave config-check examples/experiment_optimization_comparison.json
.venv/bin/qwave config-check examples/experiment_convergence_study.json
.venv/bin/qwave config-check examples/experiment_research.json
.venv/bin/qwave demo --config examples/demo.json --output results/stage5-final-demo --plot
.venv/bin/qwave optimize --config examples/optimize.json --output results/stage5-final-optimize
.venv/bin/qwave experiment smoke --output results/stage5-final-smoke
.venv/bin/qwave experiment benchmark --output results/stage5-final-benchmark
~~~

Logs and measured wall times are in results/stage5-final-logs/executed-commands.json and the named text logs. The wheel install emitted the existing nonblocking pip cache-permission warning; installation succeeded. No escalation, network package installation, cloud compute, GPU, GUI dependency or paid API was required.

## Locally completed presets

| Preset | Process wall time (s) | Held-out draws per method | Total clean/disorder trial rows | Hashed outputs | Maximum conservation error |
|---|---:|---:|---:|---:|---:|
| smoke | 5.538 | 8 | 60 | 29 | 4.88498e-15 |
| benchmark | 8.319 | 32 | 196 | 29 | 9.32587e-15 |

Both manifests have status completed. All numerical preflight/postflight screens passed, all optimized methods produced a clean-feasible observed candidate, and all evaluated solves passed conservation. There were no failed evaluation trials, undefined raw fidelities or delay-boundary optima in these two examples. A completed run can still contradict the scientific hypothesis.

Each bundle has CSV/JSON/NPZ, four figure sets in SVG/PDF/300-dpi PNG, figure descriptions, and a manifest. All 29 inventoried outputs per bundle were independently rehashed. Raw P and F were recomputed from the saved complex amplitudes and positive quadrature weights and agreed with the trial tables.

## Conditional benchmark outcomes

Benchmark has 32 paired held-out draws. The following are means, not substitutes for the raw distributions.

| Method | Held-out P | Raw conditional F | Delay-aligned F | Mean lag (ps) | Mean raw loss | Search RHS sweeps | Objective evaluations |
|---|---:|---:|---:|---:|---:|---:|---:|
| A_fixed | 0.96772137 | 0.983688833 | 0.999020361 | 0.0134175262 | 0.0242948986 | 1 | 1 |
| B_clean | 0.999704198 | 0.999780074 | 0.999993275 | -0.000271759561 | 0.000257863876 | 240 | 240 |
| C_monte_carlo | 0.997961188 | 0.998199504 | 0.999951884 | -0.00437852896 | 0.0019196536 | 240 | 48 |
| D_sensitivity | 0.998510675 | 0.967150682 | 0.99946642 | -0.0198953769 | 0.0171693216 | 201 | 67 |

Default loss is 0.5(1-P)+0.5(1-F_raw). Delay alignment is bounded to [-0.15,0.15] ps and is not used to replace raw fidelity in this loss. High aligned fidelity therefore cannot hide a raw timing mismatch.

| Difference | Mean loss difference | Family-adjusted basic-bootstrap interval | Relative percent difference | Outcome |
|---|---:|---|---:|---|
| D − A_fixed | -0.00712557699 | [-0.00884150831, -0.00507621155] | -29.3295% | supports |
| D − B_clean | 0.0169114577 | [0.0162702748, 0.0176624653] | 6558.29% | contradicts |
| D − C_monte_carlo | 0.015249668 | [0.0147145861, 0.0158653957] | 794.397% | contradicts |

These primary intervals do not cross zero. D improved the declared mean loss relative to fixed A, but performed worse than clean-state B and training Monte Carlo C in both smoke and benchmark. The overall prespecified claim of a reduction greater than 0.001 against every baseline is contradicted here. The reported large relative percentages against B reflect its very small baseline loss; absolute effects remain the primary comparison. This is not a claim about all devices, continuum transport, larger budgets or all training/initialization realizations.

All B and C starts reached their work caps in benchmark; D had one budget-stopped start. Smoke's B/C/D starts all reached their caps. Feasibility and an observed best trial are distinct from optimizer convergence. Unused capacity was not reassigned, and no held-out result reselected a candidate.

## Numerical convergence is a separate result

Diagnostics apply to the first case's configured fixed gates, with independent seeds. They are not an accuracy certificate for every optimized design. The highest tested grid is a numerical reference, not exact truth.

| Spatial nodes | dx (nm) | Clean max complex-t difference to finest |
|---:|---:|---:|
| 81 | 1 | 0.116607308 |
| 161 | 0.5 | 0.0231128906 |
| 321 | 0.25 | 0 |

| Energy nodes | dE (meV) | Clean P difference to densest |
|---:|---:|---:|
| 41 | 1.4 | 1.15174684e-08 |
| 81 | 0.7 | 2.25223407e-09 |
| 161 | 0.35 | 0 |

| K | Retained integrated variance fraction | RMS complex-t error to full covariance |
|---:|---:|---:|
| 2 | 0.389431423 | 0.0506325253 |
| 4 | 0.6838341 | 0.0308231833 |
| 8 | 0.949763057 | 0.00778473456 |

Maximum exact-discrete free-propagation amplitude error across these grids: 6.59059963e-13. The independent continuum rectangle reference includes both above- and below-barrier regimes:

| Spatial nodes | Regime | Maximum complex-t error to continuum |
|---:|---|---:|
| 81 | below | 0.0277180577 |
| 81 | above | 0.126276134 |
| 161 | below | 0.00690713708 |
| 161 | above | 0.0312939981 |
| 321 | below | 0.00172537411 |
| 321 | above | 0.00780558978 |

These measured grid/phase errors are much larger than roundoff-level probability-conservation errors. Conservation alone is therefore not a continuum-accuracy guarantee. Tiny finite-difference steps show increased cancellation relative to intermediate steps; full per-mode errors and represented-direction checks are retained.

| Diagnostic sample count | Mean fixed-design full-covariance loss | Basic-bootstrap interval |
|---:|---:|---|
| 8 | 0.0240370389 | [0.0197935116, 0.0283158886] |
| 16 | 0.0273024403 | [0.0242375462, 0.0303197868] |
| 32 | 0.0273484689 | [0.0254235713, 0.0292667709] |

These nested sample prefixes are dependent. Their largest mean is not the population truth. More draws cannot remove spatial dispersion, energy-window/quadrature error, KL omitted variance, or physical-model bias.

## Preserved development history and limits

results/stage5-development used different seed roots and was a development-only run. results/stage5-release-* preserved the first installed acceptance run. Visual review found a clipped paired-plot label and a crowded conservation-axis label; only figure layout was changed. The final run replayed the exact same scientific configs and seeds. No distribution, search criterion or confidence rule was altered.

- smoke: 264 scientific NPZ arrays were bit-for-bit identical to the prior run (provenance and timing-bootstrap arrays are intentionally excluded).
- benchmark: 264 scientific NPZ arrays were bit-for-bit identical to the prior run (provenance and timing-bootstrap arrays are intentionally excluded).

Final source and artifact audits are in results/stage5-final-logs/final-audit.json; the reproducible audit command is:

~~~sh
.venv/bin/python results/stage5-final-logs/final-audit.py
~~~

The existing stage-4 optimize command was also rerun successfully as a compatibility check. It reuses its old example seeds and is not an independent statistical replication. All five laptop presets and the research example validate; the explicit research profile was not executed. There are no unresolved implementation blockers. Scientific limitations remain: fixed-design convergence only, small held-out ensembles, finite search budgets, approximate bootstrap coverage, no independent optimization-campaign repetitions, and the idealized constant-mass coherent 1D model.

See [the full experiment design](experiments.md), [architecture and file tree](architecture.md), [the benchmark report](../results/stage5-final-benchmark/report.md), [smoke report](../results/stage5-final-smoke/report.md), and their figure_descriptions.json files.
