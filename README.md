# Phaseward

Local, CPU-only research software for electron-wave transport in an idealized
one-dimensional semiconductor. **Phaseward** is the project name; **`qwave`** is
its installable Python package and command-line program.

**Current stage: executed scientific/software audit, qwave 0.9.0.**
Start with [HOW_TO_RUN.md](HOW_TO_RUN.md) for installation, the local app and
reproducible commands. Read the [audit and limitations](docs/audit_stage9.md)
before interpreting a result. The tested laptop workflows and the larger research
benchmark execute locally; this is not a general research-readiness certificate.
The measured benchmark comparisons contradict a sensitivity-method advantage
over the clean and Monte Carlo baselines. [CONTRIBUTING.md](CONTRIBUTING.md)
sets out independent verification and development requirements.

Stationary scattering returns complex `t(E)` and
`r(E)`, transmission/reflection probabilities, and numerical diagnostics. Free,
rectangular, Gaussian, double-barrier, and user-defined potentials are supported.
Normalized energy packets now report transmitted probability, conditional output
fidelity, and optional bounded delay alignment. Derived lead reconstructions
retain the energy–wave-number Jacobian. Bounded gates, correlated potential
disorder, weighted covariance modes, complex-amplitude sensitivity diagnostics,
and measured first-order validity are implemented. Constrained multi-start gate
optimization now compares fixed, clean-state, Monte Carlo, and sensitivity
objectives under recorded solve budgets. Prespecified experiment suites now add
independent seed partitions, paired confidence intervals, raw trial distributions,
five numerical convergence studies, and automated reports. An optional local
Streamlit control panel now exposes the tested library and saved result bundles.
The sensitivity objective remains an experimental surrogate, with no
assumed advantage in throughput or conditional fidelity.

To prepare manuscript support from a specific completed, frozen experiment:

```sh
source .venv/bin/activate
qwave paper-export --run results/stage6-final-benchmark --output results/paper-benchmark-new
python3 results/paper-benchmark-new/verify_package.py
```

Choose a new output directory. Export verifies saved amplitudes, metrics, paired
statistics and all figure formats, preserves unfavorable records, and includes
parameter tables, captions, a verified-source bibliography, a literature matrix
and a pre-registration template. The LaTeX **Results section stays unfilled**.
See the [paper preparation guide](docs/paper/README.md) for scope and limits.
The bibliography is an initial abstract-level screening, not a verified novelty
claim; the previously inspected benchmark is not a new preregistered experiment.

New to quantum mechanics? Start with the [learning route](docs/derivations/README.md),
then use the [equation-to-code map](docs/derivations/code-map.md) and
[glossary](docs/derivations/glossary.md). Seven chapters derive the actual model
from its assumptions through the sensitivity surrogate. Four notebooks run
locally against the real library, without Jupyter or an account:

```sh
source .venv/bin/activate
python docs/derivations/run_notebooks.py --output results/learning-01
```

Use a fresh output name. The run saves executed notebooks, numerical checks,
exact configurations, raw data, PNG/SVG/PDF figures, and manifests. See
[the documentation index](docs/README.md) and [validation record](docs/validation_stage7.md).

## Quickstart on macOS

To open the optional local interface in this existing workspace:

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
pip install '.[dev,gui]'
streamlit run app.py
```

Open **http://127.0.0.1:8501**. The four views cover device geometry, packets and
scattering, disorder/sensitivity, and optimization/experiments. Numerical work
starts only on **Run**; jobs can be cancelled. Existing `results/` bundles open
without recomputation. Draft previews and recorded research runs are labeled
separately, with configuration, data, plot and manifest downloads.
See [the local-panel guide](docs/gui.md) and [GUI validation](docs/validation_stage6.md).
Phaseward is a project folder and local browser panel, not a macOS Applications bundle.

For the independent CLI:

Use a native Apple Silicon Python 3.11 or newer. Check `python3 --version` first.
From this directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
qwave doctor --dev
qwave config-check examples/demo.json
qwave demo --config examples/demo.json --output results/first-demo --plot
qwave config-check examples/barrier.json
qwave scatter --config examples/barrier.json --output results/first-barrier
python examples/validate_scattering.py --output results/first-validation
qwave config-check examples/wavepacket.json
qwave packet --config examples/wavepacket.json --output results/first-packet
python examples/validate_packets.py --output results/first-packet-validation
qwave config-check examples/disorder.json
qwave disorder --config examples/disorder.json --output results/first-disorder
qwave config-check examples/sensitivity.json
qwave sensitivity --config examples/sensitivity.json --output results/first-sensitivity
qwave config-check examples/optimize.json
qwave optimize --config examples/optimize.json --output results/first-optimization
```

Package installation needs internet access unless dependencies are already
cached. All installed commands work locally without accounts or network access.
NumPy, SciPy, and Matplotlib are runtime dependencies; pytest is the `dev` extra.
Streamlit is an optional `gui` extra; the CLI does not import or require it.
No Docker or GPU is used.

Run `qwave demo` for built-in defaults and a fresh timestamped results directory.
An explicit output path must not already exist. `python -m qwave` also works.
`qwave doctor` checks the runtime; `--dev` additionally requires pytest.

## Run the reproducible experiment suite

Phaseward lives in this folder. The CLI remains independent of the optional panel.

~~~sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
qwave experiment smoke --output results/my-smoke
open results/my-smoke/distributions_declared_device_0.png
qwave experiment benchmark --output results/my-benchmark
~~~

Each command writes report.md, raw CSV/NPZ/JSON, paired uncertainty estimates,
SVG/PDF/300-dpi PNG figures, and a manifest with exact seeds and output hashes.
The smoke preset uses 8 held-out draws; benchmark uses 32. A report can support,
contradict or leave the hypothesis unresolved. Failed or budget-stopped searches
remain visible. Neither preset is a claim of continuum accuracy.

The other one-command presets are:

~~~sh
qwave experiment disorder-sweep --output results/my-disorder-sweep
qwave experiment optimization-comparison --output results/my-comparison
qwave experiment convergence-study --output results/my-convergence
~~~

Use examples/experiment_*.json with --config to configure gates, packet energy,
bandwidth, sigma, correlation length, mode count, grids and seed partitions.
All designs freeze before validation or held-out draws are generated. Paired
bootstrap intervals condition on these frozen designs; they do not capture
variability across independent optimization campaigns. Numerical convergence
uses a separate diagnostic partition and never changes the final distribution.

The slower research profile runs **only** with explicit --research:

~~~sh
qwave experiment benchmark --research --output results/my-research
~~~

Choose a new directory on each run. Only the experiment command accepts explicit
--overwrite, and only for an existing suite-owned directory. Repeating a preset
repeats its seeds and is not fresh evidence. Read
[experiment design, statistics, and limitations](docs/experiments.md) and
[executed stage-5 validation](docs/validation_stage5.md).


## Run the optimization comparison

Phaseward is installed here as a Terminal command. With the existing environment:

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
qwave optimize --config examples/optimize_quick.json --output results/my-quick-optimization
open results/my-quick-optimization/optimization_tradeoffs.png
qwave optimize --config examples/optimize.json --output results/my-optimization
open results/my-optimization/optimization_costs.png
```

Use a new output directory each time. [The full example](examples/optimize.json)
compares four gates at two clean-throughput floors, with common bounds, seeded
starts, and 360 RHS-equivalent sweep units per B/C/D search. The
[quick example](examples/optimize_quick.json) uses one floor and 120 units.
No paid solver, GPU, account, or new dependency is needed.

SLSQP uses explicit clean-packet transmission and raw target-fidelity constraints,
individual/summed gate bounds, and an optional spatial gate-gradient bound.
Amplitudes are potential energies in meV, not electrode voltages. All completed
trial vectors retain objective values, physical/scaled constraint residuals,
feasibility, timing, and solve counts. Budget exhaustion and optimizer convergence
are different statuses; a selected candidate is the best feasible point actually
evaluated, not a certified global optimum.

The experimental objective is `J = sum(lambda_k * integral w |dt/deta_k|² dE)`.
The inherited convention remains `Var(eta_k)=lambda_k`, with spatially orthonormal
phi. The default weight is the incoming probability density `|A(E)|²`; a uniform
normalized energy importance is optional. Raw J and optional `J/sigma²` are
reported separately from throughput and fidelity. Complex implicit derivatives
are checked against centered finite differences; gate-step stability is audited
before searching and after freezing.

Fixed (A), clean loss (B), training Monte Carlo loss (C), and sensitivity (D)
share the same physical constraints. Distinct training/validation/held-out seeds
are saved. All designs are frozen before either evaluation ensemble is generated;
evaluation does not choose or tune a winner. Costs include separate numerical
checks and frozen-design scoring, so matched search caps are not mislabeled as
matched total wall time. The quick and full examples share seed streams.

Bundles contain JSON/CSV/NPZ, the frozen selection, every candidate's residuals,
raw complex amplitudes, raw disorder draws, hashes, and PNG/SVG/PDF figures.
Read [the optimization equations and limitations](docs/optimization.md), and
[executed checks and measured comparisons](docs/validation_stage4.md).

## Run gates, disorder, and sensitivity

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
qwave disorder --config examples/disorder.json --output results/my-disorder
qwave sensitivity --config examples/sensitivity.json --output results/my-sensitivity
open results/my-disorder/gates.png
open results/my-disorder/covariance_validation.png
open results/my-sensitivity/derivative_convergence.png
open results/my-sensitivity/linearization_error.png
```

Each output folder must be new. The default channel has **four adjustable gates**,
with individual and summed potential-energy bounds. Edit `model.gates.profiles`
to change their number, shapes, or meV amplitudes. Gaussian, raised-cosine, and
user-supplied PCHIP shapes are supported. Their smooth envelope confines them to
the channel. These parameters are potential energies, not electrode voltages.

The disorder example uses sigma=2 meV, correlation length=5 nm, a Gaussian
covariance, 4096 draws, and seed 1729. Exponential and Matérn-3/2 kernels are also
available. The covariance is built on the physical channel grid. Eight retained
KL modes are compared with full covariance samples; the reported retained
variance is measured and no normalization restores the discarded variance.
The convention is **∫φⱼφₖ dx = δⱼₖ; Var(ηₖ) = λₖ; δV = Σηₖφₖ**. Unit-variance
random coefficients `z` are stored separately from `eta`.

The sensitivity command differentiates complex `t` using symmetric real
coefficient perturbations and checks the result against an independent implicit
derivative of the discrete scattering equations. It scans perturbation steps,
reports cancellation noise, and compares first-order predictions against full
solves at increasing disorder strengths using seed 271828. **Taylor error and
omitted-mode error are reported separately.** First-order predictions can fail
or give nonphysical squared amplitudes; these outcomes are retained, not clipped.

Both bundles contain exact configs, seeds, raw complex/numerical NPZ arrays,
CSV tables, metrics, PNG/SVG/PDF figures, and hashed manifests. No optimization
or packet-fidelity claim is made by these commands. See
[gate/disorder normalization](docs/disorder.md),
[the sensitivity derivation](docs/sensitivity.md), and
[stage-3 test output and measured results](docs/validation_stage3.md).

## Run a packet on this Mac

Phaseward currently runs in Terminal; there is no separate graphical `.app` yet.
The project is in `/Users/baharyuksel/Documents/ChatGPT/Phaseward`. With the local
environment already installed:

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
qwave packet --config examples/wavepacket.json --output results/my-packet
open results/my-packet/packet_position.png
open results/my-packet/packet_spectra.png
open results/my-packet/packet_bandwidth.png
```

Use a new output folder for each run. The complete example is
[examples/wavepacket.json](examples/wavepacket.json): a 40 meV, 10 nm rectangular
barrier, a 40 meV packet center, density bandwidth 4 meV, and a free-channel target
with the same leads, mass, grid, and reference planes. The energy window is
1–100 meV with 801 nodes; the spatial domain is −40 to +40 nm with 801 nodes.
The bandwidth sweep is 1, 2, 4, 6, and 8 meV. These are illustrative choices.

`P_transmitted` is the integrated transmitted probability. Raw fidelity compares
the **normalized transmitted spectral state** with the declared target, preserving
complex phase. A tiny transmitted component can have high conditional fidelity;
the command reports throughput separately and flags it below the configured
`minimum_transmission_probability`. Unresolved normalization gives undefined
fidelity. No energy-integrated probability is called fidelity.

The optional delay alignment searches only the declared [−0.25, +0.25] ps interval
and reports the fitted lag and boundary status alongside raw fidelity. Set
`delay_alignment.enabled` to `false` to omit it. Set `reconstruction.enabled` to
`false` to omit position reconstruction; all spectral metrics and their plots
remain. Other fields remain required so the full numerical setup stays explicit.
The position figure shows the incoming left-lead component at 0 ps and outgoing
right-lead components at 0.9 ps, with unconditional densities and no viewport
renormalization. It is not a full time-dependent device-interior solution.

Each packet bundle contains the exact `config.json`, `metrics.json`, a hashed
`manifest.json`, complex `arrays.npz`, `spectrum.csv`, `potential.csv`,
`bandwidth.csv`, and `delay_scan.csv`. Optional component CSVs retain complex
spatial amplitudes. Figures are saved as PNG, SVG, and PDF. The manifest includes
source hashes, versions, constants, seeds (none used), truncation masses,
quadrature, delay settings, and reconstruction assumptions. A manifest is the
completion marker; keep it with the data.

Read [the packet equations and normalization](docs/mathematics.md) and
[measured stage-2 validation and exact commands](docs/validation_stage2.md).
The validation script generates **synthetic mathematical benchmarks**, separately
from the stationary-device packet example. The current Mac environment uses a
regular local wheel install because its editable-install `.pth` file was hidden;
the validation report records the rebuild/reinstall workaround for source changes.

## Run electron scattering

If the local environment is already installed, open Terminal and run:

```sh
cd "/Users/baharyuksel/Documents/ChatGPT/Phaseward"
source .venv/bin/activate
qwave scatter --config examples/barrier.json --output results/my-barrier
open results/my-barrier/scattering.png
```

Choose a new output directory for each run. The PNG has panels for the potential,
transmission, reflection, and unwrapped complex transmission phase. SVG and PDF
versions are saved too. `arrays.npz` retains complex amplitudes; `scattering.csv`
stores their real and imaginary parts separately. `potential.csv`, `config.json`,
`diagnostics.json`, and `manifest.json` make the calculation inspectable.

Public units are **nm and meV**, with mass specified as a ratio to the free-electron
mass. The example's ratio `0.067` is illustrative and configurable. The solver
targets the coherent constant-mass Schrödinger model using finite differences
and exact discrete leads. Its finite lead band is a numerical artifact; forbidden
energies are rejected. Grid convergence matters for complex phase as well as
probabilities. The `scatter` command supplies the stationary basis; `packet`
adds spectral throughput and conditional fidelity.

Read [the model, normalization, phase conventions, and equations](docs/scattering.md)
before interpreting results. [Stage-1 validation](docs/validation_stage1.md)
records measured errors, commands, and remaining limitations.

To change the potential, keep the common physical configuration fields and replace
the `potential` object. These complete objects are accepted:

```json
{"kind": "free", "offset_mev": 0.0}
```

```json
{"kind": "gaussian", "offset_mev": 0.0, "height_mev": 20.0, "center_nm": 0.0, "sigma_nm": 3.0}
```

```json
{"kind": "double_barrier", "offset_mev": 0.0, "height_mev": 40.0, "center_nm": 0.0, "width_nm": 4.0, "separation_nm": 12.0}
```

```json
{"kind": "tabulated", "x_nm": [-40, -10, 0, 10, 40], "values_mev": [0, 0, 30, 0, 0], "interpolation": "pchip"}
```

Tabulated profiles use explicitly declared shape-preserving cubic interpolation
and must cover the domain. Arbitrary smooth Python functions are supported by
`qwave.potentials.sample_callable`; see the API example in the model documentation.

## What the demo means

The demo integrates **f(x) = x² on [0, 1]**, entirely dimensionless. It compares
composite trapezoidal quadrature and seeded uniform Monte Carlo with the
analytical integral 1/3. The optional PNG shows only those computed polynomial
grid values. This is not an electron wave, scattering result, transmission
probability, or fidelity. No physical mapping is implied.

Each run writes `config.json`, `metrics.json`, `grid.csv`, `samples.csv`,
`arrays.npz`, and `manifest.json`, plus `demo.png` with `--plot`. Keep each bundle
together: the manifest records parameters, seeds, approximations, software and
hardware information, source hashes, UTC time, and artifact checksums. NPZ also
embeds provenance as a Unicode JSON scalar and can be read with
`numpy.load(path, allow_pickle=False)`. CSV columns include dimensionless labels.
Numerical values repeat with identical config and software; timestamps, timing,
and archive bytes are not promised to be identical. No performance gain is assumed.

## Configuration and development

`examples/demo.json` is the complete stage-0 schema. Every field is required;
unknown fields, duplicate keys, unsupported experiments, invalid units, and
non-integer seeds/sizes are rejected. `grid_points` is 2–1,000,001,
`monte_carlo_samples` is 1–1,000,000, and `seed` is 0–2⁶⁴−1. These are practical
demo limits, not physical restrictions. JSON avoids an additional YAML dependency.

See [architecture and file tree](docs/architecture.md),
[reviewed source documents](docs/source_review.md), and
[stage-0 validation](docs/validation.md), [stage-1 validation](docs/validation_stage1.md),
and [stage-2 validation](docs/validation_stage2.md).
The current gate/disorder/sensitivity evidence is in [stage-3 validation](docs/validation_stage3.md).
[AGENTS.md](AGENTS.md) records the scientific contract for future work.

## License

MIT was chosen as a short, permissive license allowing reuse, modification, and
redistribution with its copyright and license notice. See [LICENSE](LICENSE).
This license covers this repository's code and documentation; linked source
documents and third-party packages retain their own rights and licenses.
