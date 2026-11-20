# PROMPT 6 validation — 2026-11-20

Phaseward/qwave 0.7.0 adds an optional local Streamlit panel. The existing
scientific library and CLI remain independent. No objective, physical model,
prespecified test distribution or seed partition was changed based on results.
The research profile was not executed.

## Installed source and environment

All 36 package Python/marker files in
`/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/lib/python3.13/site-packages/qwave` were compared byte for byte with `src/qwave` before
testing. The 29 preexisting core files other
than the version marker are byte-identical to the previous 0.6.0 wheel. The
full audit rechecked installed/workspace equality after all runs.

Installed source SHA-256: `ea6d46261236cc44fcd76325261a58d2d750b53f4497d7266a8aae54ab6b7aae`.

Wheel: `results/stage6-final-wheels/qwave-0.7.0-py3-none-any.whl`.
Streamlit: 1.67.0, installed only through the optional GUI dependency set.
Other versions: `{"matplotlib": "3.11.2", "numpy": "2.5.5", "pip": "24.2", "pytest": "9.2.0", "python": "3.13.0", "qwave": "0.7.0", "qwave_source": "0.7.0", "scipy": "1.18.1", "setuptools": null}`.
Hardware: `{"execution_backend": "CPU", "logical_cpu_count": 8, "machine": "arm64", "native_apple_silicon_process": true, "operating_system": "Darwin", "os_release": "25.6.0", "pointer_bits": 64, "processor": "arm", "python_executable": "/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python", "python_implementation": "CPython"}`.

The workspace still has no Git commit. No commit identifier was invented;
content hashes identify the code. Source and environment metadata are stored
in each run. The existing regular-wheel installation was retained because of
the previously documented editable `.pth` issue.

## Tests

```text
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 95%]
..........                                                               [100%]
226 passed in 77.45s (0:01:17)
```

GUI/support tests exercise explicit voltage conversion, exact cache identity,
strict JSON, gate bounds, unchanged sampled potentials, manifest hashes, path
and symlink rejection, pickle-disabled NPZ, source-safe subprocesses, actual
wave computation, exported bundles, stale-result warnings, session cache reuse,
different-seed isolation, OS cancellation and partial-file retention, privacy
overrides and all four saved-suite views. The read-only tests block solver calls;
the CLI independence test blocks Streamlit imports. These tests ran with the
GUI dependency present; none were skipped.

The initial development run found a test expecting the word “overlap” while the
validator reported that seeds must be “distinct”. Saved-suite inspection then
found that preflight records lacked reflection arrays and clean evaluation
spectra had a one-row ensemble axis. The reader now selects frozen evaluation
records, validates dimensions and displays that single clean spectrum. A real
suite regression test covers the correction. The final full test run passed.

## Exact final commands

```sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage6-final-wheels .
.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage6-final-wheels/qwave-0.7.0-py3-none-any.whl
.venv/bin/python -u results/stage6-final-logs/acceptance.py
```

The acceptance script verified source identity, then executed these exact
argument lists sequentially. It set `MPLCONFIGDIR` to this workspace's
`results/.matplotlib-stage6`, `MPLBACKEND=Agg`, and removed `PYTHONPATH` so the
installed wheel was tested. Every command returned zero:

```sh
.venv/bin/python -m pytest -q
.venv/bin/qwave doctor --dev
.venv/bin/python -m pip check
.venv/bin/qwave config-check examples/demo.json
.venv/bin/qwave config-check examples/barrier.json
.venv/bin/qwave config-check examples/wavepacket.json
.venv/bin/qwave config-check examples/disorder.json
.venv/bin/qwave config-check examples/sensitivity.json
.venv/bin/qwave config-check examples/optimize.json
.venv/bin/qwave config-check examples/optimize_quick.json
.venv/bin/qwave config-check examples/experiment_smoke.json
.venv/bin/qwave config-check examples/experiment_benchmark.json
.venv/bin/qwave config-check examples/experiment_disorder_sweep.json
.venv/bin/qwave config-check examples/experiment_optimization_comparison.json
.venv/bin/qwave config-check examples/experiment_convergence_study.json
.venv/bin/qwave config-check examples/experiment_research.json
.venv/bin/qwave demo --config examples/demo.json --output results/stage6-final-demo --plot
.venv/bin/qwave scatter --config examples/barrier.json --output results/stage6-final-scatter
.venv/bin/qwave packet --config examples/wavepacket.json --output results/stage6-final-packet
.venv/bin/qwave disorder --config examples/disorder.json --output results/stage6-final-disorder
.venv/bin/qwave sensitivity --config examples/sensitivity.json --output results/stage6-final-sensitivity
.venv/bin/qwave optimize --config examples/optimize_quick.json --output results/stage6-final-optimize
.venv/bin/qwave experiment smoke --output results/stage6-final-smoke
.venv/bin/qwave experiment benchmark --output results/stage6-final-benchmark
```

Exact exit codes, wall times and log filenames are in
`results/stage6-final-logs/executed-commands.json`. Smoke finished in
5.705 s and benchmark in
8.873 s including CLI startup and output writing.
Both saved `completed` status; all five suite checks passed. These are timings
of these local executions, not guaranteed runtimes or general physical claims.
Both reuse their already declared preset seeds, so this is a reproducibility
check, not independent statistical evidence. Raw failures/stops inside searches
and method comparisons remain in the original reports.

## Live browser and worker checks

Launched the installed build with:

```sh
.venv/bin/python -m streamlit run app.py
```

The sandbox initially blocked the local port bind; the approved retry bound only
`127.0.0.1:8501`. Streamlit was downloaded into the local virtual environment
after the sandbox's package-network restriction blocked the initial download.
There is no unresolved permission blocker.

At 1365 × 900 pixels, inspected Device Builder, ran the actual wave and disorder
previews, opened the saved benchmark, and ran the laptop smoke suite through the
GUI worker. Run controls displayed elapsed time/stage logs and disabled duplicate
launches. The Cancel control was visible; a manual attempt came after the short
disorder run had already completed, so it did not cancel that run. Automated
cancellation tests verified SIGINT, terminal status and retained partial files.

The final browser log contains 166 requests, all to
the loopback origin, and zero console errors. Resource timing also reported no
external HTTP resources. Configuration disables telemetry and deployment UI;
the runtime guard rejects telemetry or non-loopback overrides. This check
describes the observed session, not every possible future third-party update.

Browser evidence: `browser-network-final.txt`, `browser-console-errors-final.txt`,
and `browser-final-state.json` under `results/stage6-final-logs/`.
Screenshots: `results/stage6-device-builder.png`, `stage6-wave-explorer.png`,
`stage6-disorder-lab.png`, and `stage6-experiments.png`. The first device screenshot
was taken during development; the other three show the final installed build.

## Computed preview examples

The exact final wave configuration is
`results/gui-jobs/20261120T163734Z-beba042113/result/config.json`, also reproduced
by `examples/gui_preview.json`. L=60 nm, four Gaussian gates with coefficients
8/15/12/6 meV at −18/−6/6/18 nm, mass=0.067 m_e, 161 spatial and energy nodes,
E0=40 meV, bandwidth=6 meV, energy window=[13,67] meV, free-channel target,
delay bounds ±0.1 ps, outgoing observation time=0.9 ps. These are illustrative
parameters, not universal material values.

| Metric | Computed value |
| --- | ---: |
| Transmitted probability | 0.967351968484 |
| Raw conditional fidelity | 0.98378663476 |
| Bounded-delay conditional fidelity | 0.999089929265 |
| Estimated delay (ps) | 0.0136059569366 |
| Maximum stationary conservation error | 1.95399e-14 |
| Nested quadrature change in P | 2.08743e-09 |
| Nested quadrature change in raw F | 1.09175e-07 |

The delay optimum is interior; no low-throughput flag was raised. Position
densities use the discrete velocity/Jacobian and remain unnormalized to the
display window. The outgoing displayed window probability is
0.966100246644,
distinct from total transmitted probability. Its coarse/fine density L1
difference is 3.46471e-05.
These checks do not establish continuum accuracy.

The final disorder configuration is
`results/gui-jobs/20261120T163839Z-96a36cbea4/result/config.json`: the same device,
Gaussian covariance σ=2 meV, ℓ=5 nm, K=4, 256 covariance samples with seed 600001,
and four independent first-order validation samples with seed 600002. Retained
integrated variance fraction: 0.683834099713.
Sampling checks passed; the selected derivative step 0.001 meV√nm differs from
the independent implicit derivative by at most
1.87951e-10. Full-solve conservation
error was at most 9.99201e-15.
The exported Taylor and KL error curves retain their observed values; no validity
outside the tested regime or optimization advantage is inferred.

The GUI experiment replay is
`results/gui-jobs/20261120T164037Z-c0bd229d66/result/` and contains the unmodified
laptop smoke configuration, the complete nested experiment manifest, plots,
raw trials, and explicit frozen-design checks.

## Output integrity and remaining limits

The audit verified all original hashes in 11 result bundles
(282 inventoried files):

| Result directory | Status | Hashed outputs |
| --- | --- | ---: |
| `results/stage6-final-demo` | legacy_completed_check_metrics | 6 |
| `results/stage6-final-scatter` | legacy_completed_check_metrics | 8 |
| `results/stage6-final-packet` | legacy_completed_check_metrics | 22 |
| `results/stage6-final-disorder` | legacy_completed_check_metrics | 21 |
| `results/stage6-final-sensitivity` | legacy_completed_check_metrics | 26 |
| `results/stage6-final-optimize` | legacy_completed_check_metrics | 27 |
| `results/stage6-final-smoke` | completed | 29 |
| `results/stage6-final-benchmark` | completed | 29 |
| `results/gui-jobs/20261120T163734Z-beba042113/result` | completed | 33 |
| `results/gui-jobs/20261120T163839Z-96a36cbea4/result` | completed | 50 |
| `results/gui-jobs/20261120T164037Z-c0bd229d66/result` | completed | 31 |

Audit commands:

```sh
.venv/bin/python results/stage6-final-logs/audit.py
.venv/bin/python results/stage6-final-logs/write_validation.py
```

No unresolved implementation blocker remains. The panel intentionally limits
opened runs/expanded NPZ/ZIP payloads to 256 MiB; larger runs remain usable through
the CLI/filesystem. A tab reload can lose its in-memory process handle while the
already launched worker finishes; use Cancel before closing. One worker per
browser session does not prevent two sessions from sharing laptop CPU. Research
scale performance was not tested. GUI screenshots and numerical consistency
checks do not replace a prespecified research/convergence pipeline.
