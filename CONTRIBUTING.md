# Contributing to Phaseward

Read [AGENTS.md](AGENTS.md) before changing code. Phaseward is the project;
`qwave` is the package/CLI. Work locally on CPU with Python 3.11+, NumPy, SciPy,
Matplotlib and pytest. Streamlit belongs only to the optional GUI extra. Do not
introduce cloud computation, account-dependent notebooks, paid APIs or telemetry.

## Start with a reproducible problem

Include the failing command, complete configuration, Python/package versions,
seed list and the relevant manifest when reporting a numerical issue. State
the physical model and expected identity independently of the code under test.
Distinguish a software defect, numerical error, model approximation and a
scientifically unfavorable result. Preserve failed runs; never “fix” a comparison
by removing unfavorable samples or changing the final distribution.

## Development and validation

Use the install instructions in [HOW_TO_RUN.md](HOW_TO_RUN.md). Verify
`qwave.__file__` before testing; this workspace uses a regular wheel, so rebuild
and reinstall after source changes. Test the installed code you intend to ship.
No linter/type-checker is configured. At minimum run:

```sh
python -m compileall -q src/qwave examples tests app.py docs/derivations
python -m pip check
pytest -q
qwave doctor --dev
qwave config-check examples/demo.json
qwave demo --config examples/demo.json --output results/contribution-demo --plot
python examples/audit_numerics.py --output results/contribution-independent
```

Use fresh directories. Follow the additional module-specific commands in
AGENTS.md. Changes to scattering require continuum/phase/conservation checks;
packets require exact spectral integrals and Jacobian/norm checks; disorder
requires sampling uncertainty and weighted covariance checks; sensitivity
requires independent derivatives and step refinement; optimization requires
fresh constraints/budgets/seed-isolation comparisons. GUI work needs both
AppTest/worker tests and a real localhost browser launch. Paper-export work
needs frozen-run semantic replay and the standalone export verifier. Executable
derivations use actual library functions, not copied solver implementations.

The `examples/independent_transport_oracles.py` audit references intentionally
import no qwave code. Do not refactor them to share the production matrix assembly,
amplitudes, units helper or packet quadrature just to reduce duplication. Their
independence is evidence. The transfer recurrence is deliberately restricted to
conditioned small systems; it is unsuitable as an opaque-barrier fallback.
Justify numerical thresholds through conditioning, observed convergence or
sampling laws. Do not loosen them solely to obtain a green test run.

## Scientific and software conventions

- Preserve complex amplitudes and declared phase planes. Public nm/meV/ps units
  must match arrays, axes, docs and manifests. Incoming/output probabilities and
  conditional fidelities are separate quantities; undefined states remain undefined.
- Preserve the weighted KL convention: `Phi.T W Phi=I`, `Var(eta)=lambda`.
  Include eigenvalues once, not twice, in sampling and the sensitivity objective.
  Gate profiles use a different sampled-peak normalization.
- Validate strict schemas. Reject complex real-potential inputs, nonfinite
  parameters, unsupported models and closed lead channels. Never silently
  change physics to finish a calculation.
- Use explicit local generators with recorded seeds. Freeze all designs before
  validation/held-out sampling. B/C/D share gate bounds, starts and search work
  caps; charge forward/response work and actual wall time. Record infeasible
  probes, numerical failures and budget stops. Postflight checks cannot reselect.
- Cache exact scientific inputs, source identity and seeds. Never round gate
  amplitudes in a cache key. GUI previews stay separate from frozen research.
- Use type annotations, focused docstrings and descriptive names. Keep the CLI
  independent of Streamlit and account/network services. Keep venv/results out
  of Git. Write new bundles, with manifests last and hashes over raw outputs.
- No invented citations, data, expected improvement, “novelty” or discovery
  claims. A change in the model or analysis requires a visible versioned record.

## Review and release evidence

A contribution should explain the concrete before/after behavior, independent
validation, commands actually executed, measured output and remaining limits.
Include plots only with underlying arrays/configurations. Review axes, units,
phase discontinuities, low-throughput flags, missing data and boundary artifacts.
An API test comparing a function to itself is not an independent scientific
benchmark. Mock/fault tests are useful for rejection paths, but do not replace
physical calculations.

For a scientific claim, specify a prospective experiment and untouched final
seeds. Development, repeated presets and audit runs are not fresh final evidence.
Package hashes without a Git commit still identify tested code, but a reviewed
source-control checkpoint should precede a future registered study. There is no
current platform/version CI matrix; report the environment actually tested.

The project uses the MIT license. Contributions must be compatible with it.
Do not copy copyrighted papers into the repository or fabricate bibliographic
metadata. A bibliography entry verifies a source's identity, not a claimed gap.
