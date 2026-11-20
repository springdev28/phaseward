# Phaseward architecture — local research and manuscript support

The paper-preparation stage adds `paper_audit.py` for read-only frozen-run
integrity, seed/design bindings, metric/statistical replay and figure replay;
`paper_export.py` for new-directory manuscript-support assembly; and installed
`paper_assets/` for bibliography, review/registration templates and LaTeX scaffolds.
The `qwave paper-export` command calls this layer without running a scattering
solver or optimizer. Original run provenance and export-time provenance remain
separate. Its data flow is: frozen manifest and arrays → consistency/replay checks
→ byte-identical evidence copies and checked support tables → export manifest.
Scientific validation is still the responsibility of the numerical/experimental
pipeline; export integrity alone establishes no physical result or novelty.

The `qwave` command line delegates to strict configuration loading, environment
diagnostics, the separate dimensionless demo, the stationary scattering runner,
the packet runner, the gated-channel disorder/sensitivity runners, or the
budgeted optimization comparison or prespecified experiment suites with a global
freeze before evaluation, paired uncertainty, and separate numerical convergence.
Scattering builds sampled potentials, solves the finite-difference system with
exact discrete leads, and exports data and figures with a manifest written last.
The packet runner solves an actual and declared target device in the same basis,
then integrates their spectra and optionally reconstructs lead components.
All computation is local and CPU-only. The optional Streamlit panel calls these
same runners through an owned local subprocess. The CLI never imports Streamlit.

| Module | Responsibility and present status |
| --- | --- |
| `config` | Strict demo/scattering/packet/disorder/sensitivity settings, targets, gate bounds, units, domains, and resource limits |
| `units` | nm/meV-to-SI conversions and separately dimensionless demo labels |
| `diagnostics` | Python, package-import, version, and CPU checks; implemented |
| `provenance` | Package source hashes, optional Git identity, artifact hashing; implemented |
| `experiments` | Separate demo and stationary-scattering result bundles with provenance |
| `packet_experiments` | Actual/target packet runs, nested quadrature checks, bandwidth sweeps, archived complex data and provenance |
| `disorder_experiments` | Gated channel preparation, empirical covariance checks, finite-difference and full-solve studies, provenance |
| `disorder_plotting` | Gate contributions, covariance/mode/sample figures, spatial/modal response, derivative and Taylor-error plots |
| `plotting` | Headless polynomial, V/T/R/phase, packet spectra, lead densities, bandwidth, and delay figures |
| `cli` | `doctor`, `config-check`, `demo`, `scatter`, `packet`, `disorder`, `sensitivity`, `optimize`, `experiment`, `--version` |
| `potentials` | Free, rectangular, Gaussian, double-barrier, tabulated and callable profiles |
| `gates` | Individually bounded peak-normalized profiles, smooth channel support, summed-potential limit |
| `scattering` | Complex flux amplitudes, probabilities, band enforcement, residuals and phase display |
| `references` | Independent continuum barrier formulas and ODE matching for validation |
| `wavepackets` | Normalized Gaussian amplitudes, positive quadrature, separate throughput/conditional fidelity, bounded delay, velocity-correct lead reconstruction |
| `disorder` | Gaussian covariance families, spatially weighted KL, local seeded sampling and empirical covariance diagnostics |
| `sensitivity` | Complex centered differences, implicit local response, step/noise studies, paired Taylor and KL errors |
| `optimization` | Exact scattering cache, normalized objectives, clean constraints, bounded gate Jacobians, budgeted SLSQP multi-start |
| `optimization_config` | Strict objectives/target/constraints, disjoint seed roles, numerical checks and CPU budgets |
| `optimization_experiments` | Preflight, common-start searches, immutable selection artifact, postflight, shared frozen-design evaluation, full candidate provenance |
| `optimization_plotting` | Observed trade-offs, objective progress, phase-by-phase costs, step diagnostics, and frozen potentials |
| `experiment_config` | Strict suite schema, configurable cases, explicit seed registry and five portable presets |
| `experiment_runner` | Global design freeze, trial evaluation, paired comparisons, automated reports, complete/failed manifests |
| `experiment_support` | Safe explicit overwrite, seeded draw vectors, per-trial metrics, descriptive statistics, CSV and invocation Git identity |
| `statistics` | Paired basic-bootstrap differences, multiplicity-adjusted intervals, effect sizes, prespecified hypothesis classification |
| `convergence` | Independent fixed-design dx, energy, KL, complex-step, sample-count diagnostics and analytical references |
| `experiment_plotting` | Empirical distributions, paired intervals, costs and convergence in SVG/PDF/300-dpi PNG |
| `gui` | Optional Streamlit views, draft/result separation, explicit Run and read-only result display |
| `gui_config` | Strict preview controls, explicit voltage-to-energy assumption, adapters to existing configs |
| `gui_visuals` | Geometry drawing from sampled or saved gate arrays, no solver |
| `gui_jobs` | Session-owned subprocess, exact preview cache, bounded cancellation and retained logs |
| `gui_worker` | Validated dispatch to existing runners, component manifests and portable envelope |
| `gui_results` | Hash-verified inventory reader, safe NPZ loading and bounded data/plot/full ZIP exports |

`app.py` is the checkout's launch entrypoint; `.streamlit/config.toml` binds to
loopback and disables usage telemetry. Worker jobs are unique directories below
`results/gui-jobs/`; each has `request.json`, `worker.log`, `job_status.json` and
`result/`. Research suites never use the preview cache. Saved result opening reads
original data and plots without invoking a runner. See [the GUI guide](gui.md).

`examples/validate_scattering.py` runs the convergence study and saves
its raw data. `examples/validate_packets.py` independently checks synthetic packet
integrals and the position representation. Research hypotheses and the
general superiority of the sensitivity objective remain unestablished. Optimization
evaluation ensembles are never passed into a search evaluator.

## File tree

```text
Phaseward/
├── .git/                         # existing repository, initially no commits
├── .gitignore
├── AGENTS.md
├── LICENSE
├── README.md
├── pyproject.toml
├── app.py
├── .streamlit/config.toml
├── examples/
│   ├── demo.json
│   ├── barrier.json
│   ├── wavepacket.json
│   ├── disorder.json
│   ├── sensitivity.json
│   ├── optimize.json
│   ├── optimize_quick.json
│   ├── experiment_smoke.json
│   ├── experiment_benchmark.json
│   ├── experiment_disorder_sweep.json
│   ├── experiment_optimization_comparison.json
│   ├── experiment_convergence_study.json
│   ├── experiment_research.json
│   ├── gui_preview.json
│   ├── validate_scattering.py
│   └── validate_packets.py
├── docs/
│   ├── architecture.md
│   ├── command_log.md
│   ├── source_review.md
│   ├── scattering.md
│   ├── mathematics.md
│   ├── disorder.md
│   ├── sensitivity.md
│   ├── optimization.md
│   ├── experiments.md
│   ├── validation_stage5.md
│   ├── gui.md
│   ├── validation_stage6.md
│   ├── validation.md              # historical PROMPT 0 evidence
│   ├── validation_stage1.md
│   ├── validation_stage2.md
│   ├── validation_stage3.md
│   └── validation_stage4.md
├── src/qwave/
│   ├── __init__.py
│   ├── __main__.py
│   ├── py.typed
│   ├── config.py
│   ├── units.py
│   ├── potentials.py
│   ├── gates.py
│   ├── scattering.py
│   ├── references.py
│   ├── wavepackets.py
│   ├── disorder.py
│   ├── sensitivity.py
│   ├── optimization.py
│   ├── optimization_config.py
│   ├── optimization_experiments.py
│   ├── optimization_plotting.py
│   ├── experiment_config.py
│   ├── experiment_runner.py
│   ├── experiment_support.py
│   ├── statistics.py
│   ├── convergence.py
│   ├── experiment_plotting.py
│   ├── experiments.py
│   ├── packet_experiments.py
│   ├── disorder_experiments.py
│   ├── disorder_plotting.py
│   ├── plotting.py
│   ├── diagnostics.py
│   ├── provenance.py
│   └── cli.py
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_demo.py
│   ├── test_cli.py
│   ├── test_scattering.py
│   ├── test_scatter_workflow.py
│   ├── test_wavepackets.py
│   ├── test_packet_workflow.py
│   ├── test_disorder.py
│   ├── test_sensitivity.py
│   ├── test_disorder_workflow.py
│   ├── test_optimization.py
│   ├── test_experiment_suite.py
│   └── test_optimization_workflow.py
├── results/                      # local generated bundles; entirely git-ignored
└── .venv/                        # local Python environment; git-ignored
```

## Numerical and provenance contract

The separate demo's only model is `f(x)=x²`, with `x ∈ [0,1]`; every quantity has unit 1.
The antiderivative gives 1/3. For `n` uniformly spaced nodes, the trapezoidal
error is `1 / (6 (n-1)²)` before roundoff. Independent tests verify this expression
and second-order convergence; their floating-point tolerances are roundoff
allowances for this polynomial, not transport accuracy requirements.

PCG64 is constructed locally with the stored seed. Monte Carlo estimates the
same unit-interval integral by averaging squared uniform samples. All samples
are retained. This demonstration does not generate physical disorder or test
the project's scientific hypothesis.

The manifest stores the complete resolved configuration, algorithm settings,
units, exact seeds, installed package versions, CPU/process details, source file
hashes, and Git commit/dirty status when available. A missing Git commit is `null`,
never invented. Installed wheels are identified by their code hashes rather than
an unrelated caller repository. The manifest inventories other artifacts, omitting
itself to avoid a circular hash. NPZ embeds the provenance before artifact hashing.
CSV and metrics JSON rely on the manifest in their directory.

Earlier commands require new result directories. The experiment suite alone
accepts explicit --overwrite for suite-owned directories. Its manifest version 2
records completed, completed_with_failed_checks, or failed; presence alone is not
success. It retains partial artifacts and a failure manifest when possible. A
directory without a manifest is incomplete. The physical solver and its independently checked
assumptions are documented in [scattering.md](scattering.md); packet normalization,
Jacobian, fidelity, delay, and display equations are in [mathematics.md](mathematics.md).
The spatial covariance convention is in [disorder.md](disorder.md), and the
derivative/Taylor derivation is in [sensitivity.md](sensitivity.md).
