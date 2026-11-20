# Phaseward wave packets: equations and numerical conventions

PROMPT 2 adds spectral packets to the constant-mass, coherent, elastic,
one-dimensional solver in [scattering.md](scattering.md). It does not change that
physics model. A packet calculation is a superposition of its stationary
scattering solutions, with a declared incoming state and target output state.
These are simulations and mathematical benchmarks, not experimental observations
or evidence for the proposed robust-control hypothesis.

PROMPT 3's gate and covariance conventions are derived separately in
[disorder.md](disorder.md); its complex transmission derivatives and first-order
expansion are in [sensitivity.md](sensitivity.md). Those diagnostics do not change
the packet normalization or turn transmission sensitivity into a fidelity.
PROMPT 4 uses these same packet metrics as explicit optimization constraints;
see [optimization.md](optimization.md) for the objectives, covariance weighting,
budgets, and frozen-design evaluation rules.

## 1. Units and the shared scattering basis

The public packet units are nm, meV, and ps. Mass is the configurable ratio
`effective_mass_ratio = m*/m_e`; the example value 0.067 is illustrative.
The code computes the kinetic coefficient using SI constants and conversions.
It obtains `HBAR_MEV_PS = hbar_SI / (MEV_TO_J * 1e-12)` from SciPy and records its
actual value, software versions, and conversions in each manifest.

With time dependence \(e^{-iEt/\hbar}\), stage 1 defines the unit-flux modes by

\[
\psi_L(x;E)=\frac{e^{ik_L(x-x_L)}+r(E)e^{-ik_L(x-x_L)}}{\sqrt{v_L(E)}},
\qquad
\psi_R(x;E)=\frac{t(E)e^{ik_R(x-x_R)}}{\sqrt{v_R(E)}}.
\]

The reference planes are \(x_L=x[0]\) and \(x_R=x[-1]\). The velocities are
positive group velocities in the respective discrete leads. Consequently
\(T=|t|^2\) and \(R=|r|^2\), including different lead velocities. A free channel
retains \(t=e^{ik(x_R-x_L)}\); its propagation phase is not set to zero.
Actual and target calculations use identical mass, leads, energy grid, spatial
grid, and reference planes. Only the configured potential is replaced for the
target. Comparisons using unrelated phase planes or basis normalizations are
not supported by the CLI.

For node spacing \(a\), the finite-difference dispersion and velocity are

\[
\tau=\frac{\hbar^2}{2m^*a^2},\qquad
E=V_\ell+2\tau[1-\cos(k_\ell a)],\qquad
v_\ell=\frac{1}{\hbar}\frac{dE}{dk_\ell}
=\frac{2\tau a}{\hbar}\sin(k_\ell a).
\]

The right-going branch has \(0<k_\ell a<\pi\) and
\(V_\ell<E<V_\ell+4\tau\). This finite upper band is a discretization artifact,
not a physical semiconductor band edge. The CLI retains the stage-1 restriction
to energies where **both** leads propagate; it does not yet include incident
energies with an evanescent right lead. It also enforces the documented numerical
band-edge guard. No rejected energy is silently converted into a different model.

## 2. Incoming amplitude, density, truncation, and quadrature

In an energy-normalized basis the incoming state is specified by a complex
amplitude \(A(E)\), with

\[
\int_W |A(E)|^2\,dE=1.
\]

\(A\) has units meV\(^{-1/2}\). Its squared modulus is a **probability density**
in energy, in meV\(^{-1}\); neither is an integrated probability. The CLI starts
with the real Gaussian amplitude

\[
A_0(E)=\frac{1}{(2\pi\sigma_E^2)^{1/4}}
       \exp\!\left[-\frac{(E-E_0)^2}{4\sigma_E^2}\right].
\]

`central_energy_mev` is \(E_0\). `bandwidth_mev` is \(\sigma_E\), the standard
deviation of the **untruncated density** \(|A_0|^2\), not of its amplitude.
After truncation, the actual mean and standard deviation need not equal these
parameters. The selected energy window \(W=[E_{\min},E_{\max}]\) lies strictly
inside the common propagating band, and contains \(E_0\). The packet is
conditioned on this window:

\[
Z_W=\int_W |A_0(E)|^2dE,\qquad
A(E)=\mathbf{1}_W(E)A_0(E)/\sqrt{Z_W}.
\]

The implementation stores Gaussian CDF masses in the common band and in the
window, their ratio, the quadrature mass before normalization, and its difference
from the analytic CDF mass. The numerical window is an additional approximation
to a Gaussian restricted only to the propagating band. Widen it when the excluded
tail mass matters. **Excluded mass is not counted as reflected probability.**
An unresolvable CDF mass is rejected rather than assigned a guessed value.

For increasing nodes \(E_0,\ldots,E_{N-1}\), positive composite trapezoidal weights
are

\[
w_0=\frac{E_1-E_0}{2},\quad
w_j=\frac{E_{j+1}-E_{j-1}}{2},\quad
w_{N-1}=\frac{E_{N-1}-E_{N-2}}{2}.
\]

Here the node subscript is unrelated to the Gaussian center notation above.
Numerical normalization uses \(Z_h=\sum_jw_j|A_0(E_j)|^2\) and replaces
\(Z_W\) by \(Z_h\). Every norm, probability, and overlap uses these same weights.
They define a positive inner product, so normalized overlaps obey
Cauchy–Schwarz up to floating-point error. Tests compare the weights with
[SciPy's independent trapezoidal implementation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.trapezoid.html),
analytic Gaussian integrals, and adaptive `scipy.integrate.quad` references.

The CLI uses an odd number of nodes and repeats the main calculation on every
other energy node, independently renormalizing that coarser packet. It stores
fine/coarse differences for both probabilities, fidelities, and the estimated
delay. Requiring even the coarse spacing to be no greater than \(\sigma_E/4\)
prevents an obviously unresolved Gaussian; it does not guarantee that an arbitrary
device resonance or phase oscillation is resolved. Refine the energy grid until
the quantities of interest converge. The synthetic study deliberately uses a
truncated spectrum with measurable, approximately second-order error.

The Python API `analyze_packet(energies_mev, incoming_amplitude, transmission,
reference_transmission, ...)` also accepts a non-Gaussian complex amplitude.
Normalize it using `quadrature_weights` first. The caller must supply physically
consistent flux amplitudes on the same energy grid and save the custom input
and its provenance; the CLI currently supports the declared Gaussian family.

## 3. Throughput and conditional output fidelity

The unnormalized transmitted spectrum and its probability are

\[
B(E)=A(E)t(E),\qquad
P_{\mathrm{trans}}=\int_W|B(E)|^2dE
=\int_W|A(E)|^2T(E)dE.
\]

Reflection is \(P_{\mathrm{refl}}=\int_W|A|^2|r|^2dE\). In the lossless
model their sum is one, subject to numerical error. The solver's per-energy flux
errors and linear residuals are stored alongside the integrated closure errors.
An energy-integrated transmission probability is never labeled fidelity.

For the declared clean reference, use \(B_{\mathrm{ref}}=A t_{\mathrm{ref}}\)
and \(P_{\mathrm{ref}}=\int_W|B_{\mathrm{ref}}|^2dE\). When both probabilities
are numerically resolved, define conditional states and their fidelity:

\[
g(E)=\frac{B(E)}{\sqrt{P_{\mathrm{trans}}}},\qquad
h(E)=\frac{B_{\mathrm{ref}}(E)}{\sqrt{P_{\mathrm{ref}}}},\qquad
F_{\mathrm{raw}}=\left|\int_W h(E)^*g(E)dE\right|^2.
\]

These spectra each have unit norm, conditioned on transmission. A constant
global phase multiplies the overlap by that phase and leaves its modulus squared
unchanged. Energy-dependent phase generally changes fidelity; replacing `t` by
`sqrt(T)` would destroy that information and is never done here.

The report always gives both transmitted probabilities and fidelity. For example,
a synthetic constant \(t=10^{-7}\) has \(P_{\mathrm{trans}}=10^{-14}\) and
unit conditional fidelity against \(t_{\mathrm{ref}}=1\). This is flagged as
low throughput, not good transport. `minimum_transmission_probability` is a
user-declared reporting threshold, not a physical constant or a censoring rule.
Resolved small probabilities retain their conditional metrics with flags.
Zero or subnormal probabilities below `float64.tiny` cannot support a numerically
reliable normalization here: the corresponding state and fidelity are `null`
in JSON (missing state arrays in NPZ). Conditional CSV densities are NaN when
undefined. Underflow does not establish exactly zero physical transmission.

Numerical values are not clipped to [0,1]; excursions of a few ulps remain visible.
Input normalization is checked to \(10^{-10}\), and elastic \(|t|^2>1+10^{-8}\)
is rejected as inconsistent input. These are numerical sanity guards, not claims
of physical accuracy. See the measured tolerances in [validation_stage2.md](validation_stage2.md).

## 4. Optional bounded delay alignment

A pure extra lag \(\delta\), under the stated time convention, multiplies the
output by \(e^{+iE\delta/\hbar}\). It gives
\(\Psi_{\mathrm{lagged}}(x,t)=\Psi_{\mathrm{target}}(x,t-\delta)\).
Positive reported delay therefore means output lag, and alignment removes it:

\[
F(s)=\left|\int_W h^*(E)g(E)
e^{-i(E-E_\star)s/\hbar}dE\right|^2,\qquad
F_{\mathrm{aligned}}=F(\hat s),\quad
\hat s\in[s_{\min},s_{\max}].
\]

The pivot \(E_\star=\sum_jw_j|A_j|^2E_j\) is the incoming mean energy.
Subtracting it only changes a global phase and improves numerical phase scaling.
Both the pivot and the positive-lag sign convention are saved. Alignment leaves
\(P_{\mathrm{trans}}\) unchanged, and `raw_fidelity` is always retained.

The finite interval must contain zero. The algorithm evaluates a declared grid,
explicitly includes zero and the endpoints, and refines each sampled local
maximum using SciPy's bounded scalar minimizer on the negative fidelity. It keeps
the best of the scanned/refined candidates; it never expands the interval.
This is a finite scan with local refinement, **not a certified global optimum**.
[SciPy documents `minimize_scalar` as a local minimizer](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize_scalar.html).
The saved scan makes multiple peaks and boundary solutions inspectable.

Two numerical guards require

\[
\Delta s\,(E_{\max}-E_{\min})/\hbar\le\pi/4,\qquad
\max(|s_{\min}|,|s_{\max}|)\max_j\Delta E_j/\hbar\le\pi/4.
\]

They limit sampling phase increments for the alignment factors; they cannot
resolve an arbitrarily oscillatory input spectrum. Reported boundary solutions
are flagged within `max(10*xatol_ps, 1e-6*interval_width)`. A scan whose score
range is at most \(10^{-12}\) is declared `unresolved_flat_scan`, retains the
zero-shift fidelity, and reports no estimated delay. Disabling alignment reports
`null` for both aligned fidelity and delay. A narrow or ambiguous scan must not
be presented as a measured physical delay.

The fitted lag is a best spectral-overlap shift relative to the target. For
dispersed or filtered packets it need not equal a density-peak shift, a unique
arrival-time observable, or a single-energy phase derivative. Report the interval,
status, and raw fidelity with it. The example uses [-0.25, +0.25] ps, 201 scan
points, and `xatol_ps=1e-7`; these are configurable choices.

## 5. Derived position representation and the energy–wave-number Jacobian

Start with a right-going wave-number representation in a uniform lead,

\[
\Psi(x,t)=\frac{1}{\sqrt{2\pi}}\int dk\,A_k(k)
e^{ik(x-x_\ell)-iEt/\hbar},\qquad
\int|A_k(k)|^2dk=1.
\]

On the monotone branch, \(dE/dk=\hbar v>0\). To preserve probability between
coordinates, \(|A_k|^2dk=|A_E|^2dE\), hence

\[
A_k(k)=\sqrt{\hbar v(E)}\,A_E(E),\qquad
\phi_E(x)=\frac{e^{ik(E)(x-x_\ell)}}{\sqrt{2\pi\hbar v(E)}}.
\]

The energy-normalized eigenfunction is the unit-flux mode times
\(1/\sqrt{2\pi\hbar}\). Substituting \(dk=dE/(\hbar v)\) gives the implemented
kernel for any right-going component with spectrum \(B\):

\[
\Psi_B(x,t)=\int_W dE\,
\frac{B(E)}{\sqrt{2\pi\hbar v(E)}}
\exp\!\left[ik(E)(x-x_\ell)-i(E-E_c)t/\hbar\right].
\]

Here \(\hbar\) is in meV ps and velocity is in nm/ps; the solver's m/s value is
multiplied by \(10^{-3}\). Thus \(\Psi\) has units nm\(^{-1/2}\), and its density
has units nm\(^{-1}\). The carrier subtraction \(E_c\), chosen as the configured
center, is a global time-dependent phase and changes no density or fidelity.
The reconstruction uses the **exact discrete** \(k(E)\) and \(v(E)\) returned
by the scattering solver. Combining continuum dispersion with discrete `t` would
mix models and is not done.

For the exact spectral integral extended over the whole uniform lead, Parseval
gives \(\int_{-\infty}^{\infty}|\Psi_B|^2dx=\int_W|B|^2dE\). The discrete
lead has a corresponding band-limited continuation: at lattice coordinates its
normalization is \(a\sum_j|\Psi_j|^2\), with the same full-line value when its
wave-number support is within the first Brillouin zone. This is an interpolation
of the numerical lead state, not an assertion of continuum convergence at finite
\(a\). Tests independently compare the reconstructed complex wavefunction with
an analytic Gaussian in position, as well as checking its integral.

For a launch offset \(s_0<0\) relative to \(x_L\), the CLI applies
\(A(E)=A_{\mathrm{Gaussian}}(E)e^{-ik_L(E)s_0}\). It centers the incoming
component upstream at time zero; this common phase cancels out of the target
overlap. The transmitted reconstruction uses \(B=A t\), the right-lead basis,
and its original propagation phase. It is **unconditional**: the full spectral
probability is \(P_{\mathrm{trans}}\), not one. The target uses \(B=A t_{\mathrm{ref}}\).

The optional figure shows the incident component on the displayed left lead at
time zero and outgoing components on the right lead at `observation_time_ps`.
It does not show a full interior scattering wavefunction, the reflected component,
or all components at one common time. No finite viewport is renormalized.
Captured window probabilities and fine/coarse energy-quadrature density
differences are saved. At a chosen early time, probability can still lie outside
the displayed outgoing lead; increasing a plotting window or waiting longer must
not be confused with increasing transmission.

A finite quadrature sum of plane waves approximates this integral on bounded
windows; it is not itself square-integrable on the entire line. Large distances
or times can produce quadrature aliasing and recurrences. Refine the energy grid
and examine larger spatial windows before interpreting tails or late-time
behavior. The spatial sampling guard `max(dx)*max(k) <= pi/2` is a basic sampling
check, not an error bound. Hard energy cutoffs also produce genuine long spatial
tails. These limitations are distinct from finite-difference spatial error,
potential-domain truncation, and the idealized physical model.

## 6. Synthetic references and interpretation

`examples/validate_packets.py` saves deterministic mathematical examples with
explicit synthetic transmission factors. They are not physical device designs
or future research results. For an effectively untruncated Gaussian density with
standard deviation \(\sigma_E\) and a unit reference factor, Gaussian integration
gives:

| Synthetic factor | Throughput | Raw conditional fidelity |
| --- | --- | --- |
| \(e^{i\varphi}\), constant global phase | 1 | 1 |
| \(e^{i(E-E_0)\delta/\hbar}\) | 1 | \(\exp[-\sigma_E^2\delta^2/\hbar^2]\) |
| \(e^{i\beta(E-E_0)^2}\) | 1 | \((1+4\beta^2\sigma_E^4)^{-1/2}\) |
| \(e^{-(E-E_0)^2/(4b^2)}\), \(q=\sigma_E^2/b^2\) | \((1+q)^{-1/2}\) | \(\sqrt{1+q}/(1+q/2)\) |
| Constant \(c\), \(0<|c|\le1\) | \(|c|^2\) | 1 |

For the pure delay, replace \(\delta\) by \(\delta-s\) in the raw-fidelity
formula. A lag outside the allowed interval therefore leaves residual mismatch
and a boundary flag. The amplitude-filter formula follows by computing
\(P=\langle|t|^2\rangle\) and \(F=|\langle t\rangle|^2/P\), separately.
The synthetic grid spans nine Gaussian standard deviations on either side;
its finite-tail discrepancy is negligible at the reported tolerances. A separate
deliberately truncated example tests non-negligible quadrature error against
independent adaptive integration.

The position-space reference starts with a Gaussian wave-number amplitude of
width \(\sigma_k\), center \(k_0\), and derived energy amplitude
\(A_E=A_k/\sqrt{\hbar v}\). At time zero its analytic transform is

\[
\Psi(x,0)=\left(\frac{2\sigma_k^2}{\pi}\right)^{1/4}
e^{-\sigma_k^2x^2+ik_0x}.
\]

This independent check detects missing velocity factors, meV/ps/nm conversion
errors, Fourier normalization errors, and phase errors. Numerical tolerances
and measured convergence appear in [validation_stage2.md](validation_stage2.md).
No analytic value is substituted for a computed output or used to force an
improvement. Raw spectra, diagnostics, settings, and unfavorable outcomes remain
in the result bundles.

## 7. Prespecified paired experiments

The experiment runner retains the packet definitions above and uses
\(L_i^{(m)}=\alpha(1-P_i^{(m)})+(1-\alpha)(1-F_{i,\mathrm{raw}}^{(m)})\)
as its declared primary evaluation loss. The optional aligned fidelity and
bounded estimated delay are separate outcomes, not replacements for raw fidelity.
The default \(\alpha=0.5\) is a design choice. An undefined normalized state
contributes zero to F only in L; the undefined F itself is preserved.

For two frozen methods on the same independent disorder realizations,
\(d_i=L_i^{(D)}-L_i^{(b)}\), \(\hat\Delta=N^{-1}\sum_i d_i\).
A paired bootstrap draws \(I_1,\ldots,I_N\) independently and uniformly from
\(\{1,\ldots,N\}\) with replacement and evaluates
\(\hat\Delta^*=N^{-1}\sum_j d_{I_j}\).
Using empirical quantiles q, the basic interval is
\([2\hat\Delta-q_{1-a/2},\,2\hat\Delta-q_{a/2}]\).
For the predeclared family of H D-versus-baseline comparisons,
\(a=(1-c)/H\) gives the Bonferroni-adjusted interval for target confidence c.
This controls multiplicity only insofar as the approximate marginal bootstrap
coverage is adequate. Small N, finite resampling, and degenerate/missing data
are explicit limitations, not evidence of certainty.

Absolute effect is \(\hat\Delta\); relative effect is
\(\hat\Delta/|\bar L_b|\), undefined at \(\bar L_b=0\), and paired standardized
effect is \(\hat\Delta/s_d\), undefined at \(s_d=0\).
The default practical improvement criterion \(\Delta<-0.001\) is prespecified,
subjective, and not a physical law. Statistical intervals are conditional on
the frozen gates, model, training data, initialization, target, quadrature,
disorder distribution and finite search budget.

Sampling uncertainty, spatial/energy discretization, KL omitted variance,
finite-difference truncation/cancellation and physical-model approximation are
different errors. In particular, \(N\to\infty\) at fixed grid and truncated
covariance estimates that approximate model's expectation ever more precisely;
it does not remove its bias relative to a continuum or a different physical
system. See [the experiment design and convergence definitions](experiments.md).

