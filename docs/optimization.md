# Constrained gate optimization and fair comparisons

PROMPT 4 optimizes gate potential-energy amplitudes in the existing coherent,
elastic, constant-mass model. It retains the finite-difference Hamiltonian,
ideal discrete leads, complex flux normalization, and phase planes from
[scattering.md](scattering.md). The objective is an **experimental surrogate**:
reducing sensitivity does not establish improved throughput or state fidelity.

## Fixed problem and energy weight

All methods share the domain, spatial/energy grids, mass, leads, background,
M gate shapes, amplitude bounds, covariance, retained K modes, incoming packet,
and fixed target potential. Only u changes:

\[
V(x;u,\eta)=V_{\rm background}(x)+\sum_j u_jg_j(x)+\sum_k\eta_k\phi_k(x).
\]

The target is independently declared and uses the same mass, leads, grid and
reference planes. The example target is the free channel. Gate amplitudes are
meV potential energies, not electrode voltages; no electrostatic conversion is
inferred.

Let q_i be positive trapezoidal energy weights in meV. The incoming Gaussian
packet obeys \(\sum_iq_i|A_i|^2=1\), restricted and renormalized to a finite window
strictly inside both propagating lead bands. Bandwidth is the standard deviation
of the untruncated probability density. Tail masses and quadrature normalization
are recorded; see [mathematics.md](mathematics.md).

The sensitivity weight is explicitly one of:

- **incoming_probability** (default): \(w_i=|A_i|^2\).
- **uniform_energy**: constant \(w_i=1/(E_{\max}-E_{\min})\).

Both have units meV⁻¹ and are normalized with q so \(\sum_iq_iw_i=1\).
Uniform importance changes the sensitivity weighting; the throughput and
fidelity constraints still use the incoming packet. No adaptive weight is
learned from evaluation samples.

## Covariance convention and objective

The inherited convention is

\[
\Phi^T W\Phi=I,\qquad \operatorname{Cov}(\eta)=\Lambda,\qquad
\eta=\sqrt{\Lambda}z,\quad z\sim N(0,I),\qquad \delta V=\Phi\eta.
\]

Here W contains spatial trapezoidal weights, phi has units nm⁻¹ᐟ²,
lambda has units meV² nm, and eta has units meV sqrt(nm).
Phi does **not** contain sqrt(lambda); see [disorder.md](disorder.md).

With \(D_{ik}(u)=\partial_{\eta_k}t(E_i;u,0)\), the candidate objective is

\[
\boxed{J(u)=\sum_iq_iw_i\sum_{k=1}^{K}\lambda_k|D_{ik}(u)|^2.}
\]

J is dimensionless. It estimates a weighted first-order mean-square **complex
amplitude change** under the retained covariance, not a probability or fidelity.
An independent identity checked in tests is

\[
\sum_k\lambda_k|D_{ik}|^2=\mathcal J_iC_K\mathcal J_i^\dagger,\qquad
D_i=\mathcal J_i\Phi,\qquad \mathcal J_{ij}=\partial_{V_j}t(E_i).
\]

This catches incorrect extra eigenvalue weighting. An independent free-channel
discrete Born formula also checks the complex derivative and objective.

**normalization=none** minimizes J. Optional **nominal_variance** minimizes
\(\bar J=J/\sigma^2\), in meV⁻². Both values are reported. At fixed kernel,
correlation length, grid and K, lambda scales as sigma², so this removes the
nominal amplitude scaling. It does not restore discarded variance, divide by
transmission, or make different kernels/truncations physically equivalent.
Sigma must be positive.

W and q prevent spurious node-count scaling. They do not remove finite-grid
dispersion, interpolation, energy quadrature or boundary sampling errors.
The spatial regression uses a smooth disorder edge to check second-order
convergence. The default hard disorder edge remains a declared approximation.

## Throughput, fidelity, loss, and explicit constraints

For the clean device and fixed target:

\[
P(u)=\sum_iq_i|A_it_i(u)|^2,\quad
P_\star=\sum_iq_i|A_it_{\star i}|^2,\quad
b_i(u)=A_it_i(u)/\sqrt{P(u)},\quad
b_{\star i}=A_it_{\star i}/\sqrt{P_\star},
\]
\[
F(u)=\left|\sum_iq_i b_{\star i}^*b_i(u)\right|^2.
\]

F is conditional on transmission. A global phase cancels, but energy-dependent
phase and timing differences remain. This stage uses raw fidelity with **no
delay alignment**. Target throughput below 1e-8 is rejected. Undefined output
fidelity stays null in reported metrics.

The same constraints apply to all methods:

\[
P(u)\ge P_{\min},\quad F(u)\ge F_{\min},\quad
u_j^{\min}\le u_j\le u_j^{\max},\quad -B\le(Gu)_n\le B.
\]

Optionally require

\[
-G_{\max}\le
\frac{(Gu)_{n+1}-(Gu)_n}{x_{n+1}-x_n}
\le G_{\max}.
\]

The optional slope bound is in meV/nm on the **sampled summed gate contribution**.
It neither bounds the background/disorder nor proves a continuum derivative
maximum. Nothing is clipped to enforce constraints.

SLSQP receives box bounds, signed nodal sum/slope linear inequalities, and P/F
nonlinear inequalities. Line-search and derivative-probe trials can violate
constraints. Every completed trial records its objective, raw residuals, scaled
residuals and feasibility. Nonnegative residuals mean satisfied. Probability/F
residuals are unscaled, box residuals divided by each width, sum by B, slope by
its bound. The configured feasibility tolerance applies to these dimensionless
residuals and is a numerical allowance, not a physical law.

No feasible observed point means **no selected optimized design**. The fixed
baseline is still evaluated and labeled infeasible when appropriate. Solver
success does not overrule a failed constraint. Tiny throughput cannot qualify
merely because its normalized transmitted shape resembles the target.

## Comparison methods

Define \(L(u,\eta)=a[1-P(u,\eta)]+(1-a)[1-F(u,\eta)]\), with the declared
transmission weight \(0<a<1\). P/F use the same packet and fixed target.
Undefined fidelity contributes zero to F **only inside this loss**; the raw
metric remains undefined.

| Method | Search objective | Search data |
| --- | --- | --- |
| A_fixed | No search; configured gates, clean L reported | Fixed physics |
| B_clean | Clean \(L(u,0)\) | Clean solves |
| C_monte_carlo | Mean L on a small fixed training disorder set | Training only |
| D_sensitivity | J or J/sigma² | Clean derivative and covariance only |

C computes full nonlinear scattering for each retained-KL training potential.
Its draws are reused at every trial to avoid resampling noise. D does not use
realized disorder samples. The **same retained-KL model** is used by C and all
final ensembles; this is not a full-covariance robustness claim. Retained
variance and the entire eigenvalue spectrum are saved.

Final evaluation additionally retains P×F (unconditional target overlap
probability), fidelity to each design's own clean output, and weighted squared
complex-amplitude change. They are separate quantities, not new names for J.
The unconditional overlap is computed directly against the normalized target,
without normalizing the output; a tiny resolvable value is not replaced by zero
when conditional fidelity is undefined.
One-standard-error summaries are descriptive finite-sample statistics. Paired
held-out loss differences use common random numbers and preserve unfavorable
comparisons; they are not automatic significance tests or population guarantees.

## Derivatives, local search, and multiple initializations

D uses the independent discrete implicit response derived in
[sensitivity.md](sensitivity.md):

\[
A\psi=b,\quad A^Ty=e_R,\quad
\mathcal J_j=\sqrt{v_R/v_L}\,y_j\psi_j/\tau,\quad D=\mathcal J\Phi.
\]

There is no conjugation in this derivative. A declared scan of centered complex
transmission differences checks it before search. Each mode must meet the
absolute error screen at a representable step. No phase unwrapping or
differentiation of |t|² substitutes for complex-t differentiation.

Gate Jacobians use real central second-order differences in meV, switching to
three-point second-order one-sided formulas at box boundaries. Absolute values
and conjugation in the real objective preclude the usual imaginary-part
complex-step shortcut. Selected and half-step gradients are compared at the
common configured start for B/C/D. Tiny-step diagnostics expose noise; they do
not automatically retune a method. A greater-than-1% representation error in a
gate perturbation is rejected. Failed preflight blocks that method's search.
Frozen designs receive a further gate-step audit; failure flags the result
without tuning, restarting, or reselecting it.

SLSQP uses \(v_j=(u_j-u_j^{\min})/(u_j^{\max}-u_j^{\min})\) in [0,1], with the
Jacobian chain rule. Each objective is divided by the recorded positive constant
max(abs(initial objective),1e-6) for conditioning, leaving minimizers unchanged.

Multi-start uses the configured vector plus seeded uniform box starts. All
methods get identical starts, even when some violate non-box constraints.
Work caps are divided equally across starts, with integer remainders assigned
to earlier starts. Unused capacity is not redistributed or spent on hidden
tuning. Iteration, work and feasibility limits are distinct.

Selection is the lowest-objective feasible **observed** trial, including saved
derivative probes and line-search points. It is not a global optimum claim.
Convergence, iteration limits, numerical failures and budget stops are stored
separately. Official interfaces:
[SciPy SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html)
and [nonlinear constraints](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.NonlinearConstraint.html).
Only public interfaces and free CPU software are used.

## Cost accounting and exact caches

A forward energy sweep costs one RHS-equivalent unit. The current implicit
response routine performs one forward sweep and a second factorization with
two RHS: three units total. Actual forward energy solves, all RHS solves, and
factorization counts are saved too. Two RHS sharing a factorization are not
assumed to take twice the time; measured wall time captures that difference.

B/C/D receive equal search caps per throughput floor. A new trial conservatively
reserves enough work to complete its objective and constraints; small unused
remainders are allowed. No partly scored candidate is reported as complete.
Common setup, preflight, search, frozen-design postflight and ensemble evaluation
costs are separated and summed by method. Plotting/serialization appears in
total bundle elapsed time. Equal search caps are **not** labeled equal total
computation or equal wall time.

Scattering caches are method-local bounded LRU caches. Keys include exact
potential, coordinate and energy bytes/shapes/dtypes, mass, both leads,
tolerance, constants, source identity, and complete scientific configuration.
Potential vectors must be finite and real. Target, gate shapes, covariance and
objective settings also enter candidate-cache context. No rounded amplitude
keys discard small perturbations. Cached arrays and lead/mass arguments are
immutable. Training arrays are copied, made read-only, and included by their
actual bytes in candidate keys. Create a new problem when changing settings. Evictions require
counted recomputation; no method reuses another method's search solves.

## Seed partition and freeze point

Example PCG64 seeds are 41001 initialization, 42001 training, 43001 validation,
44001 held out. Raw z, physical eta, potentials and starts are saved. The first
start is the configured vector; the subsequent stored starts are uniform box draws.

Every method and predeclared throughput floor finishes selecting before
**frozen_candidates.json** is written. Only then are validation and held-out
random generators called. Numerical postflight cannot alter this selection.
The file hash is checked after evaluation. Neither ensemble selects a winner,
changes a hyperparameter, or restarts a search. Validation is a separate
diagnostic set here. Common evaluation draws enable paired comparisons.

Quick/full examples share seed streams with different sample counts; they are
not independent replications. Their budgets and floors were specified before
examining held-out outputs. Reusing these scores for future adaptive tuning
would invalidate their held-out status.

## Outputs and limitations

A new result directory is required; the completion manifest is written last.
Candidate JSONL/CSV retain every completed trial's phase, objective, residuals,
timing and feasibility. NPZ preserves the associated clean t, C's training t,
D's complex derivatives, complete covariance basis, raw random draws and target.
Null means uncomputed/undefined; no fake sensitivity is inserted for clean-only
trials. Failed numerical attempts retain the attempted vector and error when
the search catches the failure.

Metrics include optimizer termination, numerical checks, per-method phase
costs, selected points and paired ensemble summaries. PNG/SVG/PDF show measured
throughput/fidelity/robustness/cost trade-offs, progress, step checks and
potentials. These points are not a certified Pareto frontier. Exit 1 reports
failed checks or a missing feasible optimized candidate while preserving the
completed bundle.

Limitations include global-phase sensitivity in J even though F ignores global
phase; clean feasibility not guaranteeing disordered feasibility; small-ensemble
overfitting and missed tails; omitted KL modes; spatial/energy and hard-edge
discretization error; local optima; numerical noise; and exhausted budgets.
Minima and raw samples remain available. The model still excludes electrode
electrostatics, decoherence, many-electron effects and laboratory validation.

See [stage-4 validation](validation_stage4.md) for executed commands, test output,
exact configurations and measured comparisons.

