# Complex transmission sensitivity and first-order validity

This stage diagnoses the response of the existing lossless scattering model to
real potential disorder. Gate amplitudes are held fixed at their configured
values. It does not optimize a device, compute a packet fidelity, or establish
robustness. The convention derived in [disorder.md](disorder.md) is used throughout:

\[
V(x;u,\eta)=V_{\mathrm{background}}(x)+\sum_j u_jg_j(x)
+\sum_{k=1}^K\eta_k\phi_k(x),\quad
\int\phi_j\phi_k dx=\delta_{jk},\quad
\mathbb E\eta_j\eta_k=\lambda_k\delta_{jk}.
\]

Thus \(\eta\) has units meV √nm; eigenvalues are not absorbed into \(\phi\).
Complex transmission \(t(E,\eta)\) remains flux normalized, with the fixed
left/right reference planes and free-propagation phase from
[scattering.md](scattering.md). All comparisons use the same energy, mass,
lead potentials, spatial grid, and reference planes.

## 1. Symmetric differences of the complex amplitude

At the clean device \(\eta=0\), define

\[
D_k(E)=\left.\frac{\partial t(E,\eta)}{\partial\eta_k}\right|_0,\qquad
D_{k,h}(E)=\frac{t(E,+h e_k)-t(E,-h e_k)}{2h}.
\]

Both real and imaginary parts are differentiated together; neither \(|t|\),
\(|t|^2\), nor an unwrapped phase is differentiated as a substitute. The code
saves complex `t_plus`, `t_minus`, and each derivative for every tested step,
energy, and mode. Magnitudes appear only in error summaries and plots after
the complex derivative has been calculated.

The coefficient perturbation is real: the physical potentials are
\(V_{\mathrm{clean}}\pm h\phi_k\). An imaginary potential would change the
stated elastic lossless model. A complex-valued output does not require an
imaginary parameter step, and the usual imaginary-part-only complex-step trick
would not recover this general complex derivative.

For a sufficiently smooth fixed-energy amplitude, Taylor expansion gives

\[
D_{k,h}=D_k+\frac{h^2}{6}\partial_{\eta_k}^3t+O(h^4).
\]

This predicts second-order truncation error while the step is numerically
resolved. Errors in the two full solves and subtraction are divided by \(h\),
so making \(h\) arbitrarily small eventually worsens the result. The report
records the measured error against the independently derived linear response
below, its best tested step for each mode, and the smallest-step error.
If that last error exceeds four times `max(best_error, eps)` and the best step
is not the last, it flags small-step error growth. This flag is a diagnostic
heuristic, not a rigorous condition-number bound.

The saved subtraction estimate
\(\epsilon(|t_+|+|t_-|)/(2h)\) accounts only for final floating-point
subtraction. It does not bound amplification of the forward-solve error, and
observed noise can exceed it. The code also checks the represented potential
direction \((V_+-V_-)/(2h)\) against \(\phi_k\). An unchanged potential, or
more than 1% infinity-norm relative direction error, is marked unresolved.
The 1% threshold is a numerical usability screen, not a physical tolerance.
It catches partial loss of a perturbation in nonzero background regions, even
when a few zero-background sites still change. Unresolved selected steps make
the CLI return a failed-check status while preserving the output bundle.

`selected_step_mev_sqrt_nm` is explicit and must occur in the studied list.
The code does not silently replace it with a fitted best step. Absolute derivative
errors are used for the study, since symmetry can make some derivatives zero;
a relative error there would be misleading or undefined. All-zero transmitted
amplitudes are flagged rather than presented as proof of an exactly insensitive
physical channel. Phase/derivative information below floating-point range
cannot be recovered by normalization.

## 2. Independent discrete linear-response check

For each energy, stage 1 solves the dimensionless system

\[
A\psi=b,\qquad A=(EI-H-\Sigma_L-\Sigma_R)/\tau.
\]

Only real onsite potential values change. With mass, leads, and energy fixed,
\(b\) and the self-energies are fixed, and

\[
\partial_{V_j}A=-\frac{1}{\tau}e_je_j^T,\qquad
\partial_{V_j}\psi=A^{-1}\frac{e_j\psi_j}{\tau}.
\]

Transmission is \(t=\gamma e_R^T\psi\), where
\(\gamma=\sqrt{v_R/v_L}\) and \(e_R\) selects the last node. Solve
\(A^Ty=e_R\) once. The complex site gradient is

\[
\boxed{J_j(E)=\frac{\partial t}{\partial V_j}
=\frac{\gamma}{\tau}y_j\psi_j,\qquad
D_k(E)=\sum_jJ_j(E)\phi_k(x_j).}
\]

The transpose is **not** a conjugate transpose; this is a derivative of a complex
amplitude, not of a real probability or objective. The implemented one-dimensional
matrix is complex symmetric, so the same banded operator solves both right-hand
sides. The check reassembles the boundary-value matrix separately and records
the difference of its baseline amplitude from `solve_scattering`, plus the
linear-system residual. It does not take finite differences internally.

The gradient has units 1/meV; \(D_k\) has units 1/(meV √nm). There is no extra
spatial quadrature factor in \(D_k=\sum_jJ_j\phi_{jk}\), since \(J\) already
differentiates the actual nodal potential parameters. For a continuum-style
display, define \(\mathcal K_j=J_j/w_j\) with the full-grid trapezoidal weights.
Then \(\sum_jw_j\mathcal K_j\delta V_j=\sum_jJ_j\delta V_j\) identically.
The plotted \(|\mathcal K(E,x)|\) has units 1/(meV nm). It is a response density
for the chosen discretization, not an independently established continuum limit.

An additional analytical test uses a free discrete lead. A perturbation of any
one onsite potential obeys the first-order discrete single-site result

\[
J_j=-\frac{i\,t_0}{2\tau\sin q},\qquad q=ka.
\]

This checks normalization, complex phase, sign, and physical units independently
of the implicit derivative assembly. Other tests perturb endpoints and interior
sites in a nontrivial Gaussian device, with equal and unequal lead velocities,
and check symmetry-protected zero derivatives. Agreement validates the derivative
of the **discrete** model; spatial convergence to the continuum model remains a
separate requirement. Previous stationary convergence studies are retained.

## 3. First-order expansion and covariance weighting

At a fixed real energy,

\[
t(E,\eta)=t_0(E)+\sum_k\eta_kD_k(E)
+\frac12\sum_{jk}\eta_j\eta_kH_{jk}(E)+\cdots.
\]

The first-order prediction is \(t_{\mathrm{lin}}=t_0+D\eta\). For a disorder
scale \(\alpha\), use \(\eta^{(\alpha)}=\alpha\sqrt\Lambda z\), keeping
\(\Phi\) and the nominal eigenvalues fixed. Thus
\(\operatorname{Cov}\eta^{(\alpha)}=\alpha^2\Lambda\), and the nominal
pointwise disorder strength before taper/truncation is \(\alpha\sigma\).

In the retained Gaussian model, first order predicts

\[
\mathbb E[\delta t]=0,\qquad
\mathbb E[|\delta t(E)|^2]=\alpha^2\sum_k\lambda_k|D_k(E)|^2.
\]

Equivalently, \(\partial t/\partial z_k=\sqrt{\lambda_k}D_k\) and the sum
is \(\alpha^2\sum_k|\partial t/\partial z_k|^2\). A later objective using
the standardized derivative must not multiply by \(\lambda\) again. A test
checks the identity against the direct nodal covariance contraction
\(J C_K J^\dagger\). The exported `dt_deta_selected`, `dt_dz_selected`, and
`predicted_mean_squared_delta_t` use these distinct names and conventions.
This diagnostic variance is not itself a fidelity, a probability, or an
optimized robustness score.

No unitary constraint is imposed on a truncated Taylor polynomial. Even a small
pure phase change can give \(|t_{\mathrm{lin}}|^2>1\) when second-order terms
are omitted. Counts of such predictions are saved. They are neither clipped nor
fed back as physical transmission probabilities. The full scattering solves
retain their independent lossless probability-conservation checks.

## 4. Full-solve validation, including omitted modes

The validation seed draws a fresh full set of Gaussian coefficients, distinct
from the example's covariance-validation seed. For each draw and every declared
\(\alpha\), the command performs:

1. A full scattering solve with the retained K-mode potential, \(t_K\).
2. The first-order prediction using the selected centered differences,
   \(t_{\mathrm{lin}}\).
3. A full scattering solve with all covariance modes from the same paired draw,
   \(t_{\mathrm{full}}\).

The three errors are kept separate:

\[
e_{\mathrm{Taylor}}=t_K-t_{\mathrm{lin}},\quad
e_{\mathrm{KL}}=t_{\mathrm{full}}-t_K,\quad
e_{\mathrm{combined}}=t_{\mathrm{full}}-t_{\mathrm{lin}}.
\]

Their complex values add, but their RMS magnitudes generally do not. A large
retained variance fraction is not substituted for a measured transport error.
The Taylor remainder is normally quadratic for sufficiently small resolved
perturbations; the omitted-mode transport error can already be first order.
Combining them into one curve would conceal that distinction.

For \(S\) draws and positive energy quadrature weights \(w_i^E\), define
\(\bar w_i^E=w_i^E/(E_{\max}-E_{\min})\). The reported metric is

\[
\mathrm{RMS}(e)=\sqrt{\frac1S\sum_{s=1}^S\sum_i\bar w_i^E|e_s(E_i)|^2}.
\]

It is a uniform-energy-window diagnostic of dimensionless complex amplitudes,
**not** weighted by a packet distribution and not a state fidelity. Per-draw
RMS errors, their median and maximum, and all raw complex full/predicted arrays
are also stored. The relative Taylor error divides by
\(\mathrm{RMS}(t_K-t_0)\); it is undefined when that denominator is at most
\(10^{-14}\), an explicitly numerical reporting floor. The zero-strength row
is retained in data but excluded from logarithmic plots.

The same draws are used across strength scales, so changes are not confounded
with changing random seeds. This pairing does not turn a small validation sample
into a population guarantee. These draws are used only to diagnose the expansion,
not to train or select a gate design. First order may fail near sharp resonances
or at moderate disorder; that outcome is kept and reported. The code never
assumes a universal small-disorder cutoff or forces the approximation to agree.

## 5. Command, plots, and reproducibility

```sh
qwave config-check examples/sensitivity.json
qwave sensitivity --config examples/sensitivity.json --output results/my-sensitivity
```

The default uses the same four-gate channel and K=8 covariance as the disorder
example. It studies 13 real coefficient steps from 1 to 1e-9 meV √nm, explicitly
selects 0.003 meV √nm, and validates 16 independent paired draws at scales
[0,0.05,0.1,0.2,0.5,1,2,4], using seed 271828. It samples 73 energies from 8 to
80 meV on the stated 0.2 nm physical grid. These are declared numerical choices,
not universal accuracy or device-performance requirements.

Figures show every gate contribution and sum, covariance eigenvalue decay and
shapes, response versus position/mode/energy, the step-convergence/noise curves,
and Taylor/KL/combined errors versus nominal disorder strength. Modes are weighted
by one coefficient standard deviation only where the axis explicitly says so.
Complex real/imaginary derivatives are exported in CSV; NPZ retains every step,
draw, energy, full potential perturbation, and full/predicted transmission.

Exact configs, seeds and roles, random generator, covariance normalization,
versions, constants, phase conventions, source hashes, approximation settings,
and artifact hashes accompany every bundle. Existing result directories are
refused; a manifest written last marks completion. See
[validation_stage3.md](validation_stage3.md) for actual outputs and numerical
tolerances. Optimization, disorder-trained gate designs, and claims of novel or
published performance remain outside this stage.
