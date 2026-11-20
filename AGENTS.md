# Phaseward: project instructions and scientific contract

## Current stage

The project name is Phaseward; its Python package and CLI remain `qwave`.
The optional local Streamlit and executable derivation stages are implemented.
The user now authorizes a full scientific/software audit, independent numerical
references, fixes, executed local validation and an honest handoff. Do not call
unexecuted research presets validated. Keep Results explicitly unfilled, verify bibliographic identities on
primary sources, label review scope and unresolved gaps, and make contributions
conditional. Exports must preserve unfavorable data, verify original hashes and
replay analysis/figures without tuning or running new optimization. Unsigned
manifests do not prove prospective registration or physical correctness.
The CLI remains independent. GUI controls preserve the scientific contracts below.
Subsequent stages still require the user's prompts. Reserved modules must not
return fabricated scientific values. Keep the stage-0 numerical demo separate
and label synthetic packet benchmarks separately from physical device examples.

## Scientific rules

- Never invent data, figures, numerical checks, citations, or experimental outcomes.
- Never hard-code an expected improvement or force the candidate method to win.
- Never describe the proposed method as novel, proven, or published without
  independently verified evidence. The current proposal is a research hypothesis.
- Never silently substitute a different physical model or normalization.
- Never confuse transmission probability with normalized transmitted-state
  fidelity. Report them separately, including negligible-transmission cases.
- Use Python to verify numerical calculations; language-model arithmetic is not
  scientific evidence. Test against independent analytical references where possible.
- Store resolved numerical parameters, software versions, exact random seeds,
  units, and approximation settings alongside every result. Record UTC time and
  source identity. Preserve raw data and failed or unfavorable outcomes.
- Use explicit SI units or a documented dimensionless convention. Do not relabel
  dimensionless demonstration arrays as physical quantities.
- Preserve complex phase. Document flux normalization, phase conventions, lead
  conditions, discretization, and convergence before making transport claims.
- Keep training, validation, and held-out disorder seeds separate in future stages.
  Compare baselines fairly and report costs, constraints, and failure cases.

## Implemented model and future scope

The project targets a coherent single electron with configurable effective mass
in an idealized one-dimensional semiconductor:

\[
i\hbar\partial_t\psi=-\frac{\hbar^2}{2m^*}\partial_x^2\psi+V(x)\psi.
\]

The planned potential energy is
\(V(x;u,\eta)=\sum_j u_jg_j(x)+\sum_k\eta_k\phi_k(x)\).
Gate amplitudes are potential-energy parameters; a conversion from electrode
voltage would require an explicitly specified electrostatic model.
Covariance-mode normalization and any eigenvalue weighting must be consistent
before constructing a sensitivity objective. PROMPT 1 uses a centered uniform
finite-difference Hamiltonian, exact retarded semi-infinite discrete leads, and
a pivoted banded solve. The mass is constant everywhere and configurable; 0.067
times the free-electron mass in examples is illustrative, not universal.
Use nm/meV at the public API and explicit SI conversion internally. Reject closed
lead channels and energies outside the allowed discrete bands. Preserve and
document the finite-band approximation, unit-flux normalization, and phase planes.
PROMPT 2 uses energy-normalized amplitudes in the same flux-normalized lead basis.
The Gaussian bandwidth is the standard deviation of the untruncated probability
density. Record finite energy-window truncation and normalization. Always report
transmitted probability alongside normalized conditional fidelity, flag low
throughput, and report undefined fidelity when a state cannot be normalized.
Preserve raw fidelity when offering bounded delay alignment; store bounds, lag,
sampling, and boundary status. Use the exact discrete velocity/Jacobian in lead
reconstructions, with no spatial display renormalization. See docs/mathematics.md.
PROMPT 3 normalizes covariance shapes with spatial trapezoidal weights:
Phi.T W Phi = I. Eigenvalues have units meV² nm; eta has units meV sqrt(nm)
and variance lambda. Disorder is Phi eta, with eta=sqrt(lambda)*z for independent
unit-variance z. Never multiply by sqrt(lambda) again or silently change this
convention in derivatives/objectives. Record retained integrated variance and
distinguish KL truncation error from Taylor-expansion error in transport.
Gate shapes have sampled peak absolute value one and bounded meV coefficients;
this is a different normalization from covariance modes. Lead potentials stay
fixed during complex-t differentiation. Use centered real coefficient steps,
inspect step convergence/cancellation noise, and retain unfavorable full-solve
comparisons. PROMPT 4 uses the identical weighted KL convention in
J=sum(lambda_k * integral w(E)|dt/deta_k|² dE). Default w=|A|²; optional uniform
energy importance is normalized explicitly. Report J and J/sigma² with their
different units; neither is a fidelity. Keep clean-throughput and raw-fidelity
constraints explicit, along with individual/summed gate and optional slope bounds.
Record infeasible trials, solver failure/budget stops, objective and residuals.
Use equal search work caps, common starts and gate bounds across B/C/D; separately
charge preflight, postflight, evaluation, forward RHS, response RHS, factorizations,
and wall times. Cache exact scientific inputs, never rounded amplitude vectors.
Training, validation and held-out seeds are distinct. Freeze all designs before
generating evaluation draws. Neither postflight checks nor held-out results may
reselect, tune, or restart a search. The sensitivity objective is an experimental
surrogate; comparisons need not favor it. Later stages still need user prompts.
Contacts, decoherence, many-electron effects, and fabrication details are outside
this intended model. Simulations are not laboratory observations.

## Engineering constraints

- For paper-export changes, verify the installed source and packaged assets,
  run `tests/test_paper_export.py` plus the required baseline checks below, and
  export an explicitly chosen frozen experiment suite to a new directory.
  Preserve the original manifest and all unfavorable records. Recompute saved
  packet/statistical quantities, replay every figure format, and run the offline
  package verifier. Keep original run and export-time identities separate. Never
  call local freeze timestamps an externally registered protocol or turn a
  successful export into a successful scientific hypothesis.

- Work locally on CPU, with Python 3.11+, NumPy, SciPy, Matplotlib, and pytest.
  No cloud compute, Docker, paid APIs, account-dependent notebooks, or devices.
- Add Streamlit only when the GUI stage begins. Keep the CLI independent.
- Use the `src/qwave/` package, semantic names, type annotations, and docstrings.
- Verify that the imported package matches the workspace before testing changes.
  The current environment uses a regular wheel install to avoid a hidden `.pth`
  issue; rebuild/reinstall after source changes, or verify a repaired editable
  install. See `docs/validation_stage1.md` for the exact installation commands.
- Preserve the independent verification algorithms in
  `examples/independent_transport_oracles.py`; they must not import qwave or
  reuse its matrix assembly. Run `python examples/audit_numerics.py --output
  <new-directory>` for scientific changes. `examples/audit_frozen_run.py` checks
  clean frozen designs without tuning or sampling new disorder. Failed forward
  residuals, response residuals, reassembled complex amplitudes, nonfinite
  derivatives/objectives and complex gate coefficients must never be selected
  by optimization. See `docs/audit_stage9.md` for evidence and limitations.
- Use explicit local NumPy generators with recorded seeds; avoid global RNG state.
- Validate configurations strictly. Reject unknown fields and unsupported models.
- Export JSON, CSV, and NPZ. Never silently overwrite existing result directories.
  A completed run has a manifest; an interrupted directory without one is incomplete.
- Run `pytest`, `qwave doctor --dev`, `qwave config-check examples/demo.json`, and
  a fresh `qwave demo` after relevant changes. Report actual outputs and blockers.
- For scattering changes also run `qwave config-check examples/barrier.json`, a
  fresh `qwave scatter` run, and `python examples/validate_scattering.py --output
  <new-directory>`. Inspect conservation, complex-amplitude convergence, and plots.
- For packet changes also run `qwave config-check examples/wavepacket.json`, a
  fresh `qwave packet --config examples/wavepacket.json --output <new-directory>`,
  and `python examples/validate_packets.py --output <new-directory>`. Inspect
  throughput, raw/aligned fidelity, delay bounds, quadrature, and spatial norms.
- For disorder/sensitivity changes also validate examples/disorder.json and
  examples/sensitivity.json, and run both `qwave disorder` and `qwave sensitivity`
  with those configs into new output directories. Inspect covariance scaling,
  retained variance, complex derivatives, noise, and measured first-order errors.
  Example seed 1729 is for covariance validation; 271828 is for independent
  linearization validation. Neither is a training or optimization seed partition.
- Keep generated results and virtual environments out of Git. A stage is complete
  only when files exist and tests execute successfully.
- For optimization changes validate both optimize examples and run a fresh
  `qwave optimize --config examples/optimize.json --output <new-directory>`.
  Inspect constraint residuals, failed/stopped searches, step stability before
  search and after freezing, held-out isolation, and costs for all four methods.
  Example seeds are 41001 (initialization), 42001 (training), 43001 (validation),
  and 44001 (held out). The quick/full examples share these draws and are not
  independent replications. Do not tune based on their held-out scores.
- PROMPT 5 exposes `qwave experiment` presets: smoke, benchmark, disorder-sweep,
  optimization-comparison, convergence-study. The research profile requires an
  explicit --research; never launch it automatically. Keep its GUI-independent
  CPU implementation and do not add later stages without a user prompt.
- Freeze every case/floor/method before generating any validation/held-out draw.
  Save and hash the prespecified plan before solves. Check all root and derived
  draw seeds for overlap across roles; paired reuse across methods/cases is
  intentional and is not independent replication. Existing preset outcomes must
  not be used to alter the final distribution, margin, target or budget.
- Preserve raw/aligned fidelity, throughput, bounded lag, conservation, failures,
  clean feasibility and phase-specific costs. Paired basic bootstrap intervals
  condition on frozen designs; Bonferroni applies only to the declared primary
  D-versus-baselines loss family. Report missing/degenerate samples, intervals
  crossing zero, and relative-effect denominator problems. No forced winner.
- Keep fixed-design dx, energy, KL, complex-step and sample-count convergence
  separate from physical findings. Larger N cannot remove solver/model bias.
  The full-covariance diagnostic must not replace retained-KL held-out evaluation.
- Suite manifest_version=2 has explicit completed/completed_with_failed_checks/
  failed status. Preserve partial artifacts on failure; a manifest alone is not
  proof of success. Only explicit --overwrite may replace suite-owned results.
- For suite changes validate examples/experiment_*.json, run pytest and the
  baseline doctor/demo checks, and run the smoke and benchmark presets into new
  directories. Verify installed source matches this workspace first. Use separate
  development/test seeds during implementation. Never tune against preset tests.
- The optional GUI must bind to 127.0.0.1 with usage telemetry disabled, use no
  remote assets/APIs, and leave non-GUI imports independent of Streamlit. Keep
  scientific work behind explicit Run actions. Geometry sampling may be live.
- Keep draft preview controls distinct from frozen result configurations. Exact
  cache keys include all scientific settings, seeds, code and runtime identity.
  Never cache a failed/incomplete result as successful or reuse preview caches
  as new research evidence. Research runs retain prespecified seeds/constraints.
- Gate energies remain meV. Voltage input requires an explicitly declared signed
  mapping in meV/mV saved in the configuration, described as illustrative rather
  than calibrated. Squared wave amplitudes are probability density, not paths.
- Saved-result opening must be read-only, verify hashes, reject unsafe paths and
  pickle arrays, and never recompute a missing artifact. Preserve failure statuses.
- Run optional AppTest and worker tests when Streamlit is installed, verify a
  localhost browser launch, and retain fresh preview/job outputs and manifests.
  Record actual tests in docs/validation_stage6.md. No GUI screenshot is evidence
  of continuum accuracy or a physical improvement.
- The derivation route is docs/derivations/README.md. Its notebooks use actual
  library functions and a standard-library runner; no Jupyter/account dependency
  is required. Keep synthetic metric checks separate from physical-model solves.
  Use educational seeds distinct from experimental partitions, retain raw data
  and failure outputs, and never claim the sensitivity surrogate is automatically
  fidelity or a failure probability. Match every equation-to-code mapping to a
  real implementation, test and generated figure. Verify references; flag any
  unresolved physical calibration or priority claim instead of inventing sources.
- After derivation/notebook changes, run the notebook runner into a fresh results
  directory, docs/derivations/check_package.py, pytest, doctor --dev, demo config
  validation, and a fresh demo. Record source identity, actual math/render checks,
  commands and numerical limits in docs/validation_stage7.md. Documentation-only
  work must not silently change the physics or add solver dependencies.
