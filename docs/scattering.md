# Phaseward stationary scattering: model and numerical conventions

## Scope and units

The assumed continuum model is

\[
-\frac{\hbar^2}{2m^*}\psi''(x)+V(x)\psi(x)=E\psi(x).
\]

It describes one coherent electron, a real scalar potential energy, and elastic
scattering. The positive effective mass is **constant across the device and both
leads**. Space-dependent masses, absorbing/complex potentials, closed lead
channels, inelasticity, contacts beyond ideal uniform leads, decoherence, and
many-electron effects are not implemented. This is a simulation model, not
hardware validation. This stationary solver supplies amplitudes to the
[packet layer](mathematics.md), which computes throughput and conditional
fidelity separately. Robustness optimization remains a future stage.

Public coordinates are nanometers, energies and potentials are millielectronvolts,
and `effective_mass_ratio` is the dimensionless ratio `m*/m_e`. Internally the
kinetic coefficient is computed in joules from meters, kilograms, and seconds.
One nm is 10⁻⁹ m; one meV is exactly 1.602176634×10⁻²² J. SciPy's actual values of
`hbar` and `m_e`, its version, and conversion factors accompany each run.
The example mass ratio 0.067 is an illustrative parameter, not a universal
semiconductor value or a material-specific device prediction.

## Discretization and the finite lead band

For uniform node spacing `a` in meters, define the kinetic hopping energy

\[
\tau=\frac{\hbar^2}{2m^*a^2},\qquad
H_{jj}=2\tau+V_j,\qquad H_{j,j+1}=H_{j+1,j}=-\tau.
\]

This is the centered second derivative. It approximates the stated continuum
model; it is not a silently substituted physical semiconductor lattice. In a
uniform lead at potential `V_l`, its plane waves obey

\[
E=V_l+2\tau[1-\cos(q_l)],\quad q_l=k_la\in(0,\pi),\quad
v_l=\frac{2\tau a}{\hbar}\sin(q_l)>0.
\]

Consequently each lead propagates only for `V_l < E < V_l + 4 tau`. Both leads
must be open. The implementation also rejects normalized energies
`(E-V_l)/(4 tau)` within `64 * float64_epsilon` of either edge, to exclude
numerically unresolved thresholds. This guard is recorded and is not a physical
energy gap. Closed channels are rejected explicitly, rather than assigned an
incorrect traveling wave.

Expanding the cosine gives
`E-V_l = hbar² k²/(2m*) - hbar² a² k⁴/(24m*) + O(a⁴ k⁶)`.
Thus the discrete velocity and phase converge to their continuum counterparts
as `ka` becomes small. An energy lying inside the discrete band is **not** by
itself a continuum-accuracy guarantee. The lead-band upper limit tends to infinity
as the grid is refined; it must not be interpreted as a real conduction-band edge.

This discretization and its low-energy limitation are also discussed in the
[Kwant continuum-discretization documentation](https://www.kwant-project.org/doc/latest/tutorial/discretize).
Kwant is a reference here, not an installed dependency or the cross-check solver.

## Incoming normalization, outgoing amplitudes, and phase

Let `x_L=x[0]`, `x_R=x[-1]`. These are the reference planes for extrapolated
uniform-lead waves, at the first and last finite-region node coordinates. With
time dependence `exp(-iEt/hbar)`, the **unit incoming flux** convention is

\[
\psi_L(x)=\frac{e^{ik_L(x-x_L)}+r\,e^{-ik_L(x-x_L)}}{\sqrt{v_L}},\qquad
\psi_R(x)=\frac{t\,e^{ik_R(x-x_R)}}{\sqrt{v_R}}.
\]

The velocities are the discrete group velocities above. The lattice probability
current is `(2 tau a/hbar) Im(psi_j* psi_{j+1})`, consistent with
`v |amplitude|²` in each uniform lead. Therefore `T=|t|²` and `R=|r|²`, including
unequal lead velocities. These probabilities are never clipped to [0,1].

Internally the solve uses incoming wave amplitude one, so its first and last
values give `r=psi[0]-1` and `t=sqrt(v_R/v_L)*psi[-1]`. This velocity factor is
essential. The returned `t` is a **flux amplitude**, not an uncorrected outgoing
wavefunction coefficient. The exact discrete potential-step test would fail if
that factor were omitted.

For a completely uniform free channel, `r=0` and
`t=exp(i k_discrete (x_R-x_L))`. The free propagation phase is retained. Moving
reference planes changes complex amplitudes; comparisons must use the same
planes and conventions. In particular, the free-channel phase need not be zero.

Plots unwrap `angle(t)` in increasing energy order; no phase is inferred from
`T`. Where `|t| <= 1e-12`, display phase is marked NaN, and unwrapping restarts
on the next resolved segment. The raw amplitudes remain unchanged. The floor is
a display rule, not a physical transmission threshold. CSV/NPZ document NaN as
unresolved phase. Coarse energy sampling can miss phase windings and resonances:
the warning for principal neighboring phase differences above 0.8π is only a
heuristic. Refine the energy grid to test phase resolution even without a warning.

## Retarded leads and stable primary solve

The outgoing boundary condition eliminates each semi-infinite lead exactly for
the discrete model. At its attached endpoint the retarded self-energy is

\[
\Sigma_l=-\tau e^{iq_l},\qquad
\Gamma_l=-2\operatorname{Im}\Sigma_l=2\tau\sin(q_l)>0.
\]

For incidence from the left, solve

\[
[E I-H-\Sigma_L|0\rangle\langle0|-\Sigma_R|N-1\rangle\langle N-1|]\psi
=i\Gamma_L|0\rangle.
\]

The code divides this equation by `tau` before solving. It uses SciPy's complex
banded solver with one upper and one lower diagonal (the pivoted tridiagonal
LAPACK path); it does not invert a dense matrix. Storage and work per energy are
linear in node count. See [SciPy solve_banded](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html).

Multiplying transfer matrices through an evanescent region mixes exponentially
growing and decaying components and can overflow or lose the transmitted part
through cancellation. This direct boundary-value solve does not construct those
growing exponential products. There is no artificial imaginary broadening or
absorbing layer. An opaque-barrier test checks finite amplitudes and flux even
when transmission underflows float64. Such underflow is not evidence of an
exactly zero physical tunneling probability; phase is unresolved there.

Numerical stability is not unlimited accuracy. Near band edges and extremely
narrow resonances the system can be ill-conditioned. Per-energy diagnostics
include `|T+R-1|` and the scaled infinity-norm linear residual

\[
\frac{\|A\psi-b\|_\infty}{\|A\|_\infty\|\psi\|_\infty+\|b\|_\infty}.
\]

A small residual measures backward consistency, not forward error or continuum
accuracy. The user-set conservation tolerance only controls a diagnostic flag
and CLI exit status; failed diagnostics remain saved for inspection.

## Potentials and boundaries

`free` is a constant potential offset in the finite region. It is a free channel
only when that offset equals both lead potentials. Each lead potential is
independently configurable, and any endpoint jump is retained and reported.

`rectangular` uses height, center, and width; `double_barrier` sums two equal
rectangles whose centers are separated by `separation_nm`. Rectangles must fit
strictly inside the domain. To avoid a one-grid-cell width bias at discontinuous
edges, `V_j` is the average over the cell `[x_j-a/2,x_j+a/2]`. The overlap length
multiplied by height/a gives partial boundary cells. This preserves integrated
barrier strength but is still an approximation to the discontinuous continuum
problem. Convergence is measured rather than assumed.

`gaussian` samples `offset + height exp(-(x-center)²/(2 sigma²))` at nodes. Outside
the finite region, uniform leads replace the Gaussian tails. Domain truncation
is separate from grid-spacing error; enlarge the region if the tails matter.
`tabulated` explicitly uses PCHIP (a shape-preserving C¹ piecewise cubic) and
requires data spanning the whole region, with no extrapolation. It is an input
representation, not an assertion that every supplied table represents a smooth
physical device.

Python API for arbitrary smooth potentials:

```python
import numpy as np
from qwave.potentials import sample_callable
from qwave.scattering import solve_scattering

x_nm = np.linspace(-40.0, 40.0, 1601)
V_mev = sample_callable(x_nm, lambda x: 18.0 * np.exp(-(x / 4.0)**2))
result = solve_scattering(
    x_nm, V_mev, np.linspace(2.0, 100.0, 401), effective_mass_ratio=0.067,
    left_lead_mev=0.0, right_lead_mev=0.0,
)
# result.t and result.r are complex; result.T and result.R are probabilities.
```

Archive custom API calculations with the exact sampled potential, original
callable/source description, all parameters, and provenance. The CLI runner
automatically archives this information for supported JSON profiles. JSON
configurations do not evaluate arbitrary Python expressions.

## Independent references and convergence

For a rectangular continuum barrier of height `V0 >= 0`, width `d`, identical
zero-potential leads, and positive energy `E`, define
`k=sqrt(2 m* E)/hbar`. Below the barrier set `kappa=sqrt(2 m*(V0-E))/hbar`;
above it set `q=sqrt(2 m*(E-V0))/hbar`. Continuity of the wavefunction and its
derivative at both faces gives

\[
T_{E<V_0}=\left[1+\frac{V_0^2\sinh^2(\kappa d)}{4E(V_0-E)}\right]^{-1},\quad
T_{E>V_0}=\left[1+\frac{V_0^2\sin^2(qd)}{4E(E-V_0)}\right]^{-1}.
\]

At `E=V0`, the limit is `T=[1+m* V0 d²/(2 hbar²)]⁻¹`. For reference planes
separated by `L >= d`, the complex transmission is

\[
t=\frac{e^{ik(L-d)}}{\cos(qd)-i\frac{k^2+q^2}{2kq}\sin(qd)}.
\]

Below the barrier `q=i kappa`; at its top the denominator is `1-i k d/2`.
The reference code evaluates probability and amplitude with separate closed
forms, using decaying exponentials/logarithms to avoid hyperbolic overflow.
It never calls the production solver. The formulas above are derived from the
stated matching conditions and checked numerically, not generated result claims.

For a nontrivial Gaussian barrier, an independently coded reference integrates
two continuum fundamental solutions using adaptive DOP853, then solves a 2×2
lead-matching system for complex `r` and `t`. It uses no finite-difference chain
or discrete dispersion. [SciPy solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html)
documents the integrator. Its tolerances are tightened separately to estimate
reference sensitivity. Fundamental-matrix matching is used only for modest
validation barriers; a condition-number guard rejects ill-conditioned matching.
It is not the production method for opaque barriers.

`examples/validate_scattering.py` preserves the actual arrays for every spacing,
the continuum references, method settings, errors, source identity, and figures.
The first study's values and test outcomes are in [validation_stage1.md](validation_stage1.md).
Tests enforce resolution-specific error limits informed by that study, not a
universal accuracy tolerance. Conservation can be excellent while discretization
phase error remains substantial; both are checked separately.

Spatial refinement reduces numerical error **within** the assumed model. It does
not fix missing real-device physics or establish effective-mass validity. This
stage makes no claim about gate optimization, robustness, or packet fidelity.
