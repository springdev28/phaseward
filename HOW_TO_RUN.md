# Running Phaseward on your Mac

Phaseward lives in `/Users/baharyuksel/Documents/ChatGPT/Phaseward`. It is a
Python project with a local browser interface, not an app in Applications.
The package and Terminal command are named **qwave**. Use a native Apple Silicon
Python 3.11 or newer. All calculations run locally on CPU. Installation downloads
free packages; the installed numerical pipeline and interface need no account,
external API, cloud service, Docker, GPU or physical device.

## Install

From Terminal, in a fresh checkout/environment:

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -c 'import qwave; print(qwave.__version__, qwave.__file__)'
pytest -q
qwave doctor --dev
```

`doctor` reports CPU/platform and installed versions. On this Mac, a historical
editable-install `.pth` issue required a regular wheel. The audited workspace
uses that working wheel installation. If imports fail or point at stale code:

```sh
python -m pip install --no-cache-dir --force-reinstall --no-deps .
python -c 'import qwave; print(qwave.__version__, qwave.__file__)'
```

Install dependencies first; `--no-deps` does not supply them. A regular install
requires reinstalling after editing `src/qwave`. See the [audit command log](docs/audit_stage9.md)
for the exact offline wheel-build/install commands actually used here. Activation
must be repeated in a new Terminal. Alternatively prefix commands with
`.venv/bin/`, for example `.venv/bin/qwave doctor --dev`.

## Open the interface

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
python -m pip install '.[gui]'
streamlit run app.py
```

Open **http://127.0.0.1:8501** in your browser. Keep Terminal open; stop with
**Ctrl+C**. If that port is occupied, use `streamlit run app.py --server.port 8503`
and open http://127.0.0.1:8503. Launch from the repository root so
`.streamlit/config.toml` disables telemetry, binds only to loopback and retains
CORS/XSRF protection. Do not enable remote sharing or usage statistics.
Streamlit is optional; the CLI remains usable without it.

The sidebar selects Device Builder, Wave & Scattering Explorer, Disorder Lab,
or Optimization & Experiments. Sliders change a draft; **Run** starts numerical
work. Device Builder's geometry preview only samples the gate shapes. Existing
results remain bound to their original settings. **Cancel** stops the job owned
by that browser session; closing a tab alone does not cancel it.

Choose **Open saved results** to read an existing `results/` folder without
recomputing it. The viewer verifies hashes and offers original configuration,
data, plot and manifest downloads. Preview settings are exploratory; research
runs use an explicitly saved suite configuration. Import `examples/gui_preview.json`
through the panel: it is a request wrapper, **not** a CLI experiment configuration.
See [GUI details](docs/gui.md) for cache identities, exports and resource limits.

## Run a first example and a real calculation

Every output name below must be new. These commands never silently replace an
existing directory. The suite alone provides an explicit `--overwrite` for
directories it owns; prefer a fresh name to preserve evidence.

```sh
qwave config-check examples/demo.json
qwave demo --config examples/demo.json --output results/my-first-demo --plot
qwave scatter --config examples/barrier.json --output results/my-barrier
qwave packet --config examples/wavepacket.json --output results/my-packet
qwave disorder --config examples/disorder.json --output results/my-disorder
qwave sensitivity --config examples/sensitivity.json --output results/my-sensitivity
qwave optimize --config examples/optimize_quick.json --output results/my-optimization
```

The demo is a dimensionless polynomial integration check, **not electron
scattering**. The remaining commands use the documented constant-mass, coherent,
elastic 1D model. Public units are nm, meV and ps; gate strengths are potential
energies. Electrode voltages need a separately declared electrostatic mapping.
The example mass `0.067 m_e` is illustrative, not universal.

## Research workflow

1. Read [the mathematics](docs/mathematics.md), [model assumptions](docs/scattering.md),
   and [learning route](docs/derivations/README.md). State a target state and a
   falsifiable hypothesis using the [pre-registration template](src/qwave/paper_assets/preregistration_template.md).
2. Develop numerical accuracy and parameter choices using analytic/development
   checks. Refine spatial and energy grids, KL modes and derivative steps.
   Use independent optimization restarts to assess search variability.
3. Freeze physical settings, constraints, budgets, comparisons and all seed
   partitions **before** final evaluation. Never tune from the held-out scores.
   Repeated presets reuse their seeds: a replay is not an independent replication.
4. Run a laptop preset and inspect the entire bundle, including failed trials:

   ```sh
   qwave experiment smoke --output results/my-smoke
   qwave experiment benchmark --output results/my-benchmark
   qwave experiment optimization-comparison --output results/my-comparison
   qwave experiment disorder-sweep --output results/my-sweep
   qwave experiment convergence-study --output results/my-convergence
   ```

   A complete custom configuration uses the matching preset, for example
   `qwave experiment benchmark --config examples/experiment_benchmark.json --output results/my-custom-benchmark`.
   Smoke uses 8 held-out draws; benchmark and laptop optimization-comparison use
   32. These are workflow examples, not statistical-power guarantees.
5. Inspect `run_plan.json`, `frozen_candidates.json`, `seeds.json`,
   `summary.json`, trial-level CSV/NPZ, costs, numerical diagnostics and
   `report.md`. Read actual feasibility and stop reasons; an exhausted search
   budget is not convergence of the optimizer. Validation and final draws are
   generated only after all designs freeze. A/B/C/D share bounds; B/C/D share
   RHS-equivalent search caps and starting points. Actual work, factorization
   counts and wall times are separate; they need not be equal.
6. Export a **specific frozen suite run** for manuscript support:

   ```sh
   qwave paper-export --run results/my-benchmark --output results/my-paper-support
   python results/my-paper-support/verify_package.py
   ```

   This verifies and replays saved analyses/figures, copies the chosen evidence,
   and leaves the paper's Results section unfilled. It does not discover a result
   or prove novelty. Preserve source/version compatibility; never bypass a
   hash or analysis-compatibility rejection.

The slower profile requires explicit opt-in:
`qwave experiment benchmark --research --output results/my-research-benchmark`.
It completed locally in the audit (128 held-out draws), but this is one prescribed
configuration. The name “research” does not establish accuracy or generality.
See [experiment design and statistical interpretation](docs/experiments.md).

## Reproduce the figures

Each command saves raw arrays, settings, versions, units, seeds where applicable
and a manifest. Preserve the whole directory, not just its PNG. SVG/PDF/PNG are
generated by scientific workflows; the stage-0 demo emits a PNG only. The
following entry points cover all figure families; numerical studies have their
own exact settings recorded in their manifests and executable source.

| Figure family | Reproduction command (fresh output directory) |
|---|---|
| Polynomial demo | `qwave demo --config examples/demo.json --output results/repro-demo --plot` |
| Potential, T, R and transmission phase | `qwave scatter --config examples/barrier.json --output results/repro-scatter` |
| Packet spectra, lead densities, phase and bandwidth metrics | `qwave packet --config examples/wavepacket.json --output results/repro-packet` |
| Gates, disorder samples, covariance and KL modes | `qwave disorder --config examples/disorder.json --output results/repro-disorder` |
| Sensitivity, finite-difference steps, Taylor and KL error | `qwave sensitivity --config examples/sensitivity.json --output results/repro-sensitivity` |
| Objective/constraints, trade-offs, method costs | `qwave optimize --config examples/optimize.json --output results/repro-optimize` |
| Held-out distributions, paired intervals and five convergence studies | `qwave experiment benchmark --output results/repro-benchmark` |
| Independent continuum and scattering benchmarks | `python examples/validate_scattering.py --output results/repro-scattering-checks` |
| Deterministic synthetic packet benchmarks | `python examples/validate_packets.py --output results/repro-packet-checks` |
| Independent audit references and convergence | `python examples/audit_numerics.py --output results/repro-independent` |
| Frozen-design clean feasibility and grid refinement | `python examples/audit_frozen_run.py --run results/my-comparison --output results/repro-frozen-checks` |
| Teaching notebooks and their figures | `python docs/derivations/run_notebooks.py --output results/repro-learning` |
| Exact figure replay from a frozen suite | `qwave paper-export --run results/my-benchmark --output results/repro-paper` |

For your own run, replace the example configuration with that run's `config.json`
and use its preset name. Exported `figure_index.csv` binds manuscript figures to
their measured source. Pixel-identical reproduction is only expected with the
same rendering stack; timestamps can differ. A changed numerical model is a new
experiment, not reproduction of an old plot.

## Add a disorder model without changing its meaning

The installed kernels are Gaussian, exponential and Matérn-3/2. To add a kernel:

1. Define its covariance, units and meaning of `sigma_mev`/`correlation_length_nm`
   in `docs/disorder.md`. A valid covariance must be positive semidefinite on
   the grid. A different covariance is an explicit model extension.
2. Add the formula and strict allowed-name validation in
   `src/qwave/disorder.py` and the matching configuration/UI validation
   (`src/qwave/config.py`, `src/qwave/gui_config.py`, `src/qwave/gui.py` as applicable).
   Do not add an undocumented jitter, fallback kernel or variance rescale.
3. Preserve `Phi.T W Phi = I`, `Var(eta_k)=lambda_k`, and
   `deltaV=Phi eta`, with `eta=sqrt(lambda)*z`. Eigenvalues carry meV² nm;
   shapes carry nm⁻¹/². A non-Gaussian coefficient law needs its own explicit
   schema, higher-order assumptions and sampler; covariance alone does not
   specify that law.
4. Add independent formula/PSD/grid-refinement checks and a second sampling
   factorization or known analytic covariance. Assess sample uncertainty; do
   not force empirical variance to equal the target in each draw. Verify taper
   effects and retained variance. Preserve exact seeds and coefficient arrays.
5. Test strict config validation, sensitivity normalization, all optimization
   methods and fresh manifests. Reinstall after source edits. Update examples,
   docs and the equation-to-code map. Never retrofit a held-out distribution
   because a new model yields favorable scores.

## Interpret failures and limitations

Exit 0 means that command's implemented checks passed; it is not a certificate
of continuum accuracy, optimizer optimality or a physical discovery. CLI exit 1
means diagnostic checks failed; exit 2 usually indicates invalid input, an I/O
problem, unavailable optional dependency or numerical rejection. Preserve logs.
`completed_with_failed_checks` is not a passing experiment. A directory lacking
its final manifest is incomplete. Older manifests lack explicit status: inspect
their metrics instead of assuming success.

- **Forbidden energy:** both discrete leads must propagate. Check lead offsets,
  mass and spacing; changing the grid changes the finite numerical band. There
  is a roundoff guard at each edge. Never clip energies into the band silently.
- **T+R differs from 1 / response rejected:** investigate residuals, conditioning,
  band edges and grid settings. The optimizer rejects nonfinite responses and
  failed numerical screens. Passing conservation does not establish phase or
  continuum accuracy.
- **High fidelity with low P:** conditional output shape can be good while almost
  nothing transmits. Report both P and raw F. Zero/unresolvable transmission
  gives undefined fidelity, not zero loss. Keep throughput constraints active.
- **Delay at its bound / flat alignment:** retain raw fidelity and declared
  bounds. A flat or boundary optimum does not identify an unrestricted delay.
- **Wave-packet ghosts or missing mass:** inspect coarse/fine density differences,
  window probabilities, phase sampling and energy/position grids. Reconstructions
  are asymptotic lead components, not the full inside-device state or a trajectory.
  Finite-window density is never renormalized to look complete.
- **Covariance rank failure:** fine smooth kernels can have unresolved tiny
  eigenvalues. Reduce retained K or change the explicitly documented resolution;
  do not fabricate modes. A hard channel cutoff changes boundary scattering.
- **Derivative noise / infeasibility / budget stop:** inspect the recorded step
  studies, constraints and solver messages. More starts or budget may be a future
  development experiment; never restart based on final test scores.
- **Integrity mismatch:** keep the original bundle and investigate. A manifest
  hash detects edits; it does not prove honest prospective registration or physics.

Known limits: constant mass, one coherent elastic channel, ideal leads, no
interactions, contacts, decoherence, electrostatic calibration or hardware
validation. Dense covariance work has an 801-node channel guard. The surrogate
J is not failure probability or fidelity. LAPTOP presets have small training
sets and finite search budgets; convergence of a fixed diagnostic device does
not certify every optimized potential. This audit covers one Apple Silicon
machine/Python environment, not the entire supported-version/platform matrix.
No linter or static type checker is configured; byte compilation and the test
suite are separate checks. See [audit findings, measured results and the next
experiment](docs/audit_stage9.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
