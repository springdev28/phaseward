# Prespecified experiments (PROMPT 5)

Phaseward runs locally on CPU. The CLI is an installed Terminal command, not a
macOS graphical application. The five portable presets are built into the
package; they do not depend on the current directory containing example files.

~~~sh
qwave experiment smoke --output results/smoke
qwave experiment benchmark --output results/benchmark
qwave experiment disorder-sweep --output results/disorder-sweep
qwave experiment optimization-comparison --output results/comparison
qwave experiment convergence-study --output results/convergence
~~~

A new output directory is mandatory. Only an explicit --overwrite can replace a
directory previously created by this suite runner. Foreign directories,
symlinks, the working directory and its ancestors are protected. Earlier stage
commands still always require a new directory.

The laptop smoke preset has four gates, 81 spatial nodes, 41 energies, K=3,
two starts, 90 RHS-equivalent sweeps per optimized method, and 2/4/8
training/validation/held-out draws. The benchmark has 161 nodes, 57 energies,
K=6, 240 search sweeps and 4/12/32 draws. These are **finite-budget workflow
demonstrations**, not accuracy or statistical-power guarantees. Both also run
the five numerical diagnostics below. The examples share physical settings but
have distinct seed roots; changing both numerical resolution and seeds means
their scores are not a controlled comparison of sample size.

The disorder sweep prespecifies sigma=1,2,4 meV, shares random coefficients
across cases, and freezes all cases before any held-out evaluation. The
optimization comparison prespecifies clean-transmission floors 0.85 and 0.98.
The convergence-study preset uses more mode/sample/energy levels. No preset
picks a case, threshold or test distribution after seeing its outcome.

The slower research profile requires an explicit flag:

~~~sh
qwave experiment benchmark --research --output results/research-benchmark
qwave experiment benchmark --config examples/experiment_research.json --research --output results/custom-research
~~~

It uses three starts, 600 search sweeps per optimized method, 8 training,
32 validation and 128 held-out draws, plus larger convergence grids. It is
never a fallback and never run by a normal preset. The benchmark research profile
was explicitly executed in the [stage-9 audit](audit_stage9.md), including its
128 held-out samples. Other research-profile variants were not run. This profile name does not confer scientific
validity; design-specific convergence, power planning and independent
optimization repetitions are still necessary.

## Configuring independent variables

The complete strict JSON examples are examples/experiment_*.json. Load one with
--config and the matching preset name. All fields are required; unknown keys,
duplicate JSON keys, nonfinite values, unsupported models, invalid energy bands
and seed overlap are rejected.

| Variable | Configuration field |
|---|---|
| Gate count, positions and shapes | optimization.model.gates.profiles (replace the list; one entry per gate) |
| Gate amplitude/bounds | each profile's amplitude_mev and bounds_mev |
| Packet center and bandwidth | optimization.packet.central_energy_mev / bandwidth_mev |
| Disorder sigma and ell | optimization.model.disorder.sigma_mev / correlation_length_nm |
| Kernel and optional taper | optimization.model.disorder.kernel / boundary_taper_nm |
| Retained covariance modes | optimization.model.disorder.retained_modes |
| Spatial grid | optimization.model.scattering.grid_points, x_min_nm, x_max_nm |
| Energy quadrature | optimization.model.scattering.energy_min_mev, energy_max_mev, energy_points |
| Bounded delay search | delay: enabled, min_ps, max_ps, grid_points, xatol_ps |
| Statistical design | statistics, optimization.ensembles |
| Numerical-study axes | convergence |

Each case has a unique name and overrides limited to model/packet. Dictionaries
merge recursively, lists replace lists. Thus a gate-profile list changes M,
including custom smooth tabulated profiles. All B/C/D methods retain identical
gate counts, bounds, search caps, starts, targets and feasibility tests **within
a case**; cases may have different physics. No method receives extra held-out
information. Input gates are potential energies, not voltages. Effective mass
is constant/configurable; 0.067 m_e is an illustrative example.

## Seeds and the global freeze barrier

Six distinct uint64 roots are declared: initialization, training, validation,
held-out, convergence, bootstrap. SeedSequence(root).spawn(n) materializes one
uint64 seed per disorder draw; each initializes a local PCG64 and generates one
standard-normal vector. Root and derived seeds are all checked for duplicates.
An increased count keeps the same prefix. Exact roots, draw lists, realized z,
eta, potentials, eigenvectors and eigenvalues are saved.

Within a role, the same list is deliberately reused across methods/floors/cases
for paired comparison. That is common random numbers, not independent
replication. No seed is shared across stochastic roles. The overlap check is
within one suite, not a global database of all past runs; repeating a preset is
a replay, not fresh evidence. PROMPT-5 preset roots differ from the earlier
stage-4 example roots.

For the inherited convention Phi^T W Phi=I, eta=sqrt(lambda) z and deltaV=Phi eta;
Var(eta)=lambda. The solver's complex phase, finite lead dispersion, normalization
and SI conversions are unchanged. The candidate objective remains
J=sum_k lambda_k integral w |dt/deta_k|² dE, with w=|A|² by default. Optional
uniform w is normalized. J, J/sigma², throughput and conditional fidelity are
different quantities.

The runner writes and hashes run_plan.json **before solves**. It creates only
training draws while searching all cases/floors/methods, then writes and hashes
frozen_candidates.json. Postflight checks may flag a frozen design but cannot
change it. Only then are validation and held-out draws generated. Validation is
a development diagnostic in this version; it does not choose a winner, tune a
parameter, or trigger another search. Tests instrument this ordering across
multiple cases. The configuration and distribution never change during a run.

This is an auditable local prespecification artifact, not external registration.
A human can still edit a future config; doing so after reviewing outcomes is a
new exploratory design and must not be represented as an untouched final test.

## Metrics, costs and statistical interpretation

Every clean and disorder trial stores P, raw F, bounded-delay-aligned F, estimated
lag (ps), delay-boundary status, low-throughput flags, maximum |T+R-1|,
linear-system residual, solve time, analysis time, seed and feasibility context.
A positive lag means later arrival relative to the declared target. Default
alignment is restricted to [-0.15,0.15] ps with an 81-point scan and 1e-7 ps local
refinement tolerance. The sampling guards come from the packet implementation.
Raw fidelity remains the clean constraint and primary loss. Zero or unresolved
transmission leaves fidelity undefined; a high conditional F never replaces P.

The primary loss is alpha(1-P)+(1-alpha)(1-F_raw), default alpha=0.5.
When F is undefined it contributes zero to F **only in that loss**, retaining the
undefined state in all raw outputs. Failed solves remain failed rows and prevent
an eligible hypothesis classification; they are not silently dropped to improve
a mean. Defined-only summaries report their denominators.

Search costs are equal RHS-equivalent caps, not equal wall times. One ordinary
energy sweep costs one; an implicit-response evaluation costs three including
the independent forward solve. Target setup, gate/mode preflight, search,
postflight, evaluation and convergence costs are saved separately. Distinct
completed objective evaluations, cache hits, forward energy solves, response
RHS, factorizations, constraint residuals, budget stops and failed starts remain
available. Selected trials can be finite-difference probes. Feasibility,
SLSQP convergence and a global optimum are different claims.

For each metric and method pair on N common held-out draws, d_i=y_i,second-y_i,first.
The effect is mean(d). Independently drawing N indices with replacement, using
the **same indices for the two methods**, gives bootstrap means d*. A basic
bootstrap interval is [2 mean(d)-q_(1-a/2)(d*), 2 mean(d)-q_(a/2)(d*)].
This is the reverse-percentile/bootstrap-basic method, cross-checked against
SciPy in tests. Index generation is batched to bound temporary memory.
No resampling or normality assumption about independent method outcomes is used.

The predeclared primary family is D-versus-A/B/C raw loss across every case and
floor. Its intervals use Bonferroni a=(1-confidence)/family_size; other intervals
are marginal/exploratory. Bonferroni does not require independence across cases,
but it cannot make approximate bootstrap coverage exact. Default 4000 resamples
must give at least ten expected draws per adjusted tail for classification.
Small held-out samples and few tail resamples can give unstable intervals.
Degenerate empirical differences are flagged and classified unresolved rather
than presented as population certainty.

Absolute differences, unadjusted/adjusted CIs, explicit zero-crossing flags,
relative effect mean(d)/abs(mean(first)) and percent, and paired d_z=mean(d)/sd(d)
are saved. Relative effects are undefined at a zero denominator and can be
unstable near zero. d_z is undefined with zero empirical variance. Missing
pairs and their counts are retained; no hypothesis support is inferred from
incomplete paired loss samples.

The default minimum meaningful benefit is 0.001 raw-loss units: a **declared
design criterion, not a physical law**. With delta=D-baseline, support requires
the adjusted interval entirely below -0.001. Contradiction means its lower
bound is above -0.001, excluding the declared benefit; this includes clear
harm as well as effects too small for that criterion. Crossing the margin is
unresolved. Ineligible designs, missing values, inadequate tails and degenerate
samples are also unresolved. Overall support requires support against every
baseline; one eligible contradiction contradicts that combined hypothesis.
All favorable and unfavorable pairwise outcomes stay in the report.

Inference is conditional on the specified **discrete** model, finite energy
window, retained-KL distribution, fixed target, training data, budgets and
frozen designs. It does not integrate over optimizer initialization or training
variability, does not prove physical superiority, and does not establish
generalization to full-covariance disorder or a real semiconductor.

## Five convergence axes and independent benchmarks

All diagnostics use the **configured fixed gates of the first case**, a separate
convergence seed partition, and no search. They never tune or reselect a design.

1. Spatial nodes: the same analytic gate profiles and one PCHIP-interpolated
   disorder field from the finest-grid full covariance are sampled at each
   spacing. The physical field is fixed rather than redrawn as the eigenbasis
   changes. It is zero outside the finite channel. The finest result is a
   numerical reference, not continuum truth; fixed endpoint planes preserve
   dispersion-induced phase error. Gate sampled-peak normalization is recomputed
   and can contribute a documented discretization effect for off-grid peaks.
2. Energy nodes: keep the finest spatial grid and physical field fixed. Refine
   positive trapezoidal quadrature over the same finite energy window,
   renormalizing the same Gaussian density. Store P/F/lag changes to the
   densest grid without declaring an arbitrary tolerance a physical law.
3. KL truncation: on one fixed spatial grid use one full eigensystem, the same
   z_i prefixes, and compare each K to all covariance modes. Retained integrated
   variance is recorded and lost variance is not restored by rescaling.
   Preserve each paired trial's amplitude/metric errors. This studies an
   approximation and does not change the final retained-KL test distribution.
4. Real coefficient steps: compare centered differences of **complex** t to the
   independent implicit response, per mode/energy. Save direction-representation
   errors as well as h-dependent truncation and cancellation errors.
5. Sample counts: use nested prefixes from independent diagnostic draws for the
   fixed full-covariance design, showing sample means, standard errors and basic
   bootstrap intervals. Prefix estimates are dependent and the largest sample
   mean is not population truth. Increasing N cannot repair biased spatial or
   energy discretization or a wrong physical model.

Exact discrete free propagation and an independently coded continuum rectangular
barrier (30 meV, width 8 nm) are checked at each spatial level above/below its
height. Benchmarks have declared zero leads; nonzero-lead configurations and
grids that cannot exactly represent the benchmark width receive explicit skip
records. They are not replacements for the configured physical device.
The 1e-8 conservation screen is inherited from stage-1 convergence/roundoff tests,
not a bound on transmission or phase discretization error.

Convergence on this fixed design does **not** certify all optimized designs.
Additional energy/grid studies at every reported optimum, independent optimizer
campaigns, power analysis and realistic physical models remain outside the
current empirical claims. All numerical convergence figures are labeled
separately from method-comparison findings.

## Bundle and completion semantics

Each run saves config.json, run_plan.json, seeds.json, frozen_candidates.json,
summary.json, report.md, trials.json/CSV, candidates.jsonl/CSV, paired_differences.csv,
costs.csv, convergence.json/CSV, arrays.npz, figure_descriptions.json and
SVG/PDF/300-dpi PNG figures. NPZ uses numeric/complex arrays and a Unicode JSON
provenance scalar; load with allow_pickle=False. Confidence distributions and
raw amplitudes are preserved. Every figure comes from saved numerical arrays.

The final manifest records UTC, configuration/resolved cases, exact seeds,
versions, CPU hardware/process, source-file hashes and Git identity when available,
scientific conventions, artifact hashes and sizes. The current repository has
no commit; null is reported, never an invented hash. A wheel's source hashes
identify the installed code; an invocation checkout is recorded separately when
available. Source changes during a run invalidate its completed status.

The suite's manifest_version=2 has an explicit status: completed,
completed_with_failed_checks, or failed. A failed suite still preserves partial
rows, seeds, failure.json and an inventory. An interrupted directory without a
manifest is incomplete; the mere presence of a v2 manifest does not imply success.
No plots or numerical outcomes are fabricated to fill a failed run.

References for the implemented numerical interfaces:
[SciPy paired/basic bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
and [NumPy SeedSequence spawning](https://numpy.org/doc/stable/reference/random/parallel.html).
The mathematical and physical conventions are derived in mathematics.md,
scattering.md, disorder.md and sensitivity.md.

