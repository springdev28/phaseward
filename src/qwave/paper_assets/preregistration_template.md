# Phaseward prospective experiment-registration template

**DRAFT — NOT REGISTERED.** Complete every `[REQUIRED]` field before generating or
inspecting final evaluation draws. Archive the signed-off protocol, config,
source/dependency hashes and a timestamped immutable copy. A local timestamp or
manifest hash is not external registration. Existing inspected smoke/benchmark
data are development evidence and cannot become a newly preregistered test set.

## Identity, scope and falsifiable primary hypothesis

- Protocol ID, authors, UTC freeze date, archive location: `[REQUIRED]`.
- Model: coherent, elastic, constant-effective-mass, single-electron 1D scattering;
  uniform ideal leads; discrete finite band explicitly enforced. No hardware claim.
- Population of interest: `[REQUIRED: distribution of channel potentials and
  device parameters; state whether conditioning on particular trained designs]`.
- Candidate D: constrained covariance-weighted complex-transmission sensitivity.
- Baselines A/B/C: fixed gates / clean loss optimization / direct Monte Carlo
  loss optimization on a training disorder ensemble. Same gate shapes, counts,
  bounds, targets, constraints and available tuning information.
- Primary loss per trial:
  \(L=\alpha(1-P)+(1-\alpha)(1-F_{\rm raw})\), with
  `[REQUIRED: alpha in [0,1]]`. P is integrated transmitted probability and F is
  normalized conditional fidelity to `[REQUIRED: frozen target and phase planes]`.
  The two quantities must also be reported separately.
- Primary hypothesis: for **each** baseline b in `{A,B,C}`, D reduces the
  held-out expected loss by more than `[REQUIRED: delta > 0]`:
  \(\Delta_b=\mathbb E[L_D-L_b]<-\delta\), while satisfying every common clean
  feasibility constraint. State whether cases form one family or separate studies.
- Null for each comparison: \(\Delta_b\geq-\delta\). Joint support requires
  all prespecified upper simultaneous confidence limits below -delta; no
  post-hoc replacement of a baseline or primary metric. A lower limit above
  -delta contradicts the stipulated meaningful improvement; it does not
  necessarily demonstrate harm. Otherwise classify unresolved. Numerical or
  feasibility failure prevents a confirmatory support claim.
- Select confidence level, family correction and inference method before testing:
  `[REQUIRED]`. Default implementation uses paired basic bootstrap with
  Bonferroni primary-family adjustment; coverage is approximate. Declare
  resample count, seed and required empirical tail support. Very small samples
  or degenerate empirical differences do not establish population certainty.

## Outcomes, failure handling and comparisons

Primary: held-out raw loss under the above definition. Secondary: P, raw F,
bounded delay-aligned F, estimated lag in ps and boundary-hit frequency,
low-throughput frequency, clean feasibility, conservation and residual errors,
wall time, forward/response RHS work, factorizations and candidate counts.
Delay alignment must retain raw F and cannot be used to redefine the primary
metric after inspection. Bounds/grid/tolerance: `[REQUIRED]`.

Define negligible transmission threshold `[REQUIRED]`. Undefined F remains null
in tables. If following the current loss policy, explicitly accept F=0 **only
inside loss** for unresolved normalization; that is a loss convention, not a
measured fidelity. Specify failed-solver handling `[REQUIRED]`; do not silently
drop failures. Current code excludes missing pairs with counts and blocks
confirmatory support when evaluation failures occur. No feasible design means
an unavailable comparison, not permission to substitute a successful restart.

Report absolute paired differences, relative differences with denominator
definition and undefined zero-baseline cases, interval zero crossings and
practical-margin crossings. State that conditioning on one training ensemble
does not estimate variability across training or optimizer initializations.
Independent campaign repetitions and the unit of inference: `[REQUIRED]`.

## Allowed parameter ranges and exact chosen design

Fill both allowed ranges and the finite planned grid before the final evaluation.
All ranges are scientific choices, not universal physical constants.

| Variable | Unit | Allowed range | Planned values / frozen config path |
|---|---|---|---|
| Constant effective mass | free-electron masses | [REQUIRED: positive] | [REQUIRED] |
| Channel and lead reference planes | nm | [REQUIRED] | [REQUIRED] |
| Gate count M; positions; widths/shapes | count; nm | [REQUIRED] | [REQUIRED] |
| Gate amplitude bounds; total potential bound | meV | [REQUIRED] | [REQUIRED] |
| Optional summed spatial gradient bound | meV/nm | [REQUIRED or disabled] | [REQUIRED] |
| Packet central energy; density standard deviation | meV | [REQUIRED] | [REQUIRED] |
| Open-band integration window and energy nodes | meV; count | [REQUIRED] | [REQUIRED] |
| Disorder amplitude sigma; correlation length ell | meV; nm | [REQUIRED] | [REQUIRED] |
| Covariance kernel; taper and physical channel support | declared kernel; nm | [REQUIRED] | [REQUIRED] |
| KL rank K; retained integrated variance | count; fraction | [REQUIRED] | [REQUIRED] |
| Spatial grid; finite-difference modal step | nm; meV sqrt(nm) | [REQUIRED] | [REQUIRED] |
| Minimum clean P and raw F | dimensionless | [REQUIRED: in [0,1]] | [REQUIRED] |
| Training/validation/held-out sample counts | count | [REQUIRED] | [REQUIRED] |
| Common optimizer starts, work caps, stopping settings | counts and declared units | [REQUIRED] | [REQUIRED] |

Maintain the mode convention \(\Phi^T W\Phi=I\),
\(\eta_k=\sqrt{\lambda_k}z_k\), \(\operatorname{Var}\eta_k=\lambda_k\).
Eigenvalues have units meV² nm. Differentiate with respect to eta; do not weight
by lambda twice. Gate shapes use a different, peak normalization.

## Seed splitting and design freezing

1. Archive exact nonoverlapping initialization, training, validation, held-out,
   convergence and bootstrap root/child seed lists. Reject duplicate seeds and
   accidental partition overlap. Specify generator and seed derivation.
2. Tune using training/development only within `[REQUIRED: fixed search protocol]`.
   If development informs protocol changes, record them and freeze a new protocol
   before using a genuinely untouched final evaluation set.
3. Fix every A/B/C/D design before generating any final evaluation fields. Pair
   all methods on exactly the same evaluation draws. Cases sharing draws are
   dependent and must not be pooled as independent observations.
4. No postflight or held-out score may reselect, retune or restart a search. Keep
   all attempted candidates, budget stops, infeasible designs and negative results.
5. For repeated studies, check overlap across previous manifests as well as
   within the new run. Repeating a preset reuses its seeds; it is not replication.

## Numerical accuracy requirements and failure criteria

Before the final run, set and justify error budgets from development convergence:
`[REQUIRED: thresholds and evidence for each item below]`.

- Open-lead energy validity, analytical free/barrier checks, complex phase planes.
- Spatial grid convergence of complex t, P and F; independent-method cross-check.
- Energy quadrature convergence and finite-window missing mass.
- KL rank convergence against full-covariance draws, separate from Taylor error.
- Modal derivative step convergence, implicit-response agreement and noise floor.
- First-order prediction error across prespecified small/moderate sigma ranges.
- Losslessness and solve residual checks; conservation alone does not demonstrate
  continuum accuracy. Sample count cannot repair solver bias.
- Apply relevant checks to optimized as well as fixed devices before making
  accuracy claims. Current suite convergence checks on first-case fixed gates
  are insufficient to certify every optimized candidate.
- Sample-count precision targets and a fixed stopping rule. Do not keep adding
  draws until a favorable interval appears. Any sequential design needs its
  own preregistered valid inference procedure.

Failures include mismatched hashes, seed leakage, changed targets/distributions,
budget inequity, unsupported energies, unresolved derivative steps, failed
conservation/convergence, missing trials, constraint violations or unreproducible
figures. Preserve the run and label it failed/unresolved as appropriate. Record
amendments and their timing; separate exploratory follow-up from confirmation.

## Sign-off

Before access to final outcomes: `[REQUIRED: reviewers, date, config hash, source
hash, seed-list hash, designated primary family and decision rule]`.
After running: record deviations and outcomes without rewriting this frozen plan.
