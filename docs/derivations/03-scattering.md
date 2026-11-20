# 3. Stationary scattering, flux, and a stable numerical solve

Prerequisites: Chapters 1–2. The continuum model is S3. Only one channel in each
uniform semi-infinite lead is used, with constant mass everywhere and real
potential. Both leads must propagate at every requested energy.

<a id="eq-s4"></a>
## S4. Fix phase planes before defining amplitudes

Let `x_L<x_R` be reference planes, and let `k_L,k_R>0` and `v_L,v_R>0` be the
wave numbers and group speeds in the leads. Using consistent length/time units,
define a left-incident **flux basis** by

$$
\chi_E(x)=\frac{e^{ik_L(x-x_L)}+r(E)e^{-ik_L(x-x_L)}}{\sqrt{v_L}}
\quad\hbox{in the left lead},\qquad
\chi_E(x)=\frac{t(E)e^{ik_R(x-x_R)}}{\sqrt{v_R}}
\quad\hbox{in the right lead}.
$$

`t(E)` and `r(E)` are dimensionless complex channel coefficients. The chosen
stationary basis functions have units `(time/length)^(1/2)`; unlike a normalized
packet they are not probability amplitudes with units `length^(-1/2)`. “Unit
flux” means their incoming current coefficient is one in this basis. Multiplying
by an incident coefficient with units `time^(-1/2)` gives a physical current in
`time^-1`. Chapter 4 introduces the additional factor needed for an
energy-normalized basis. No finite integral of `|χ_E|²` is set to one here.

Substitute a sum of the two waves into S2. The interference terms in the
**current** cancel: their contribution to `χ*χ'` is real. The incident,
reflected, and transmitted currents therefore have coefficients `1`, `-|r|²`,
and `|t|²`. Their ratios give

$$
R(E)=|r(E)|^2,\qquad T(E)=|t(E)|^2,\qquad T(E)+R(E)=1.
$$

The last equality follows from real, static, lossless scattering and identical
current through either boundary, not from the definitions alone. If instead a
solver uses incident spatial coefficient one and transmitted spatial
coefficient `c_R`, it must return

$$
t=\sqrt{\frac{v_R}{v_L}}c_R,\qquad T=\frac{v_R}{v_L}|c_R|^2.
$$

All ratios here are dimensionless. Using $T=|c_R|^2$ for unequal speeds violates
flux normalization. For a free channel with identical leads, the phase-plane
convention gives $t=\exp(ikL)$ and $r=0$, where $L=x_R-x_L$. A convention with
$t=1$ for free propagation is also possible, but it is **not this API**.
Changing phase planes changes amplitudes' phases. Packet comparisons must use
the same planes, lead definitions, and incoming spectrum.

<a id="eq-s5"></a>
## S5. From the differential equation to a discrete lead band

Take a uniform grid $x_n=x_L+na$, with spacing `a>0`, indices $n=0,\ldots,N-1$,
and real nodal potentials `V_n`. Smooth enough functions obey

$$
\chi''(x_n)=\frac{\chi_{n+1}-2\chi_n+\chi_{n-1}}{a^2}+O(a^2).
$$

The remainder has units of a second derivative, with a fourth derivative in
its coefficient. It assumes bounded higher derivatives; discontinuous
potentials and their sampling need a separate convergence check. Define the
positive hopping energy $\tau=\hbar^2/(2m^*a^2)$, using SI when constructing it. The
resulting discrete stationary equation is

$$
-\tau\chi_{n-1}+(2\tau+V_n)\chi_n-\tau\chi_{n+1}=E\chi_n.
$$

In a uniform lead, insert $\chi_n=\exp(iqn)$ and use
$e^{iq}+e^{-iq}=2\cos q$ to obtain

$$
E=V_\ell+2\tau(1-\cos q_\ell),\qquad
q_\ell= k_\ell a\in(0,\pi),\qquad
v_\ell=\frac{1}{\hbar}\frac{dE}{dk_\ell}
=\frac{2\tau a}{\hbar}\sin q_\ell.
$$

Here `q_ell` is dimensionless, `τ,E,V_ell` are energies, `k_ell` is inverse
length, and `v_ell` is length/time. The discrete open band is strictly
$V_\ell<E<V_\ell+4\tau$. The implementation also rejects a roundoff-sized region at
each edge; speed tends to zero there and flux normalization is singular.
The requested energy window must lie inside the **intersection** of both
bands. A closed transmitted lead is explicitly unsupported, not reported as
a fabricated propagating result.

Expanding cosine at small `ka` gives

$$
E-V_\ell=\frac{\hbar^2k_\ell^2}{2m^*}
\left[1-\frac{(k_\ell a)^2}{12}+O((k_\ell a)^4)\right].
$$

Thus the continuum dispersion is recovered only with resolved wavelengths.
The finite band is a discretization artifact, not a semiconductor band-structure
prediction. Spatial refinement must compare at fixed physical energies and
device dimensions, not fixed fractions of the moving discrete band.

<a id="eq-s6"></a>
## S6. The current consistent with this discretization

For nodal packet values `Ψ_n` with units `length^(-1/2)`, use the lattice norm
$a\sum_n|\Psi_n|^2$ on the infinite uniform lattice. Applying the same product-rule
calculation as S2 to its time-dependent discrete equation gives

$$
\partial_{t_{\rm obs}}|\Psi_n|^2
=\frac{j_{n-1/2}-j_{n+1/2}}{a},\qquad
j_{n+1/2}=\frac{2\tau a}{\hbar}\operatorname{Im}(\Psi_n^*\Psi_{n+1}).
$$

The bond current has units `time^-1`. Inserting a plane wave of spatial
coefficient `c` gives $j=v|c|^2$ with the **discrete** velocity in S5. If states
were instead normalized as $\sum_n|\Psi_n|^2=1$, their node amplitudes and current
formula would carry different powers of `a`. qwave's reconstructed physical
density uses the first convention. Spatial trapezoidal weights used for KL
modes are a different finite-interval integration problem.

<a id="eq-s7"></a>
## S7. Eliminate the leads, including the incoming source sign

For the actual linear solve, let the incident **spatial** coefficient be one
and denote the dimensionless nodal solution by `ψ`. Then
$\psi_0=1+r$ and $\psi_{N-1}=c_R$. With the same wave phases as S4, the left ghost node
and right outgoing ghost node are

$$
\psi_{-1}=e^{-iq_L}+r e^{iq_L}
=e^{iq_L}\psi_0-2i\sin q_L,\qquad
\psi_N=e^{iq_R}\psi_{N-1}.
$$

All quantities in this equation are dimensionless. Substitution into the first
and last rows of $(EI-H)\psi=0$ leaves the finite system

$$
\mathcal A\psi=b,\qquad
\mathcal A=\frac{EI-H-\Sigma_L e_0e_0^T-\Sigma_R e_{N-1}e_{N-1}^T}{\tau},
\qquad b=2i\sin q_L\,e_0,\qquad
\Sigma_\ell=-\tau e^{iq_\ell}.
$$

`H` is the `N×N` finite Hamiltonian with diagonal `2τ+V_n` and neighboring
entries `-τ`; `e_n` is the dimensionless unit coordinate vector. `Σ_ell` has
energy units; the dimensionless matrix `A` (written `mathcal A` above) has
off-diagonal entries `+1`, diagonal `(E-V_n)/τ-2`, and an added $\exp(iq)$ at each
boundary. The self-energy's negative imaginary part imposes an outgoing,
retarded boundary for the $\exp(-iEt_{\rm obs}/\hbar)$ time convention. In energy units
the source is `iΓ_L e_0` with $\Gamma_L=-2\operatorname{Im}\Sigma_L=2\tau\sin q_L>0$.

After the solve,

$$
r=\psi_0-1,\qquad
t=\sqrt{\frac{\sin q_R}{\sin q_L}}\,\psi_{N-1}.
$$

Constant mass and common spacing make the sine ratio equal to the velocity
ratio. These equations are exact for the stated discrete lead model up to
linear-solve roundoff. They are not an approximation using a finite absorbing
box. Lead potentials stay fixed when a channel potential is varied.

### Why use a banded solve?

`solve_scattering` uses a pivoted complex banded solve, with linear storage and
work per energy for this tridiagonal problem. It never repeatedly multiplies
transfer matrices containing both growing and decaying evanescent factors.
Such products can lose the small transmitted component exponentially in a
thick barrier. Eliminating outgoing leads and solving the boundary-value system
avoids that specific instability.

This is not a promise of perfect conditioning. Sharp resonances, near-edge
speeds, very small transmission, and subtraction in $r=\psi_0-1$ can still be
delicate. A small residual is a backward-error check; forward error also depends
on conditioning. A value underflowing to zero is numerically unresolved, not
proof of exact zero transmission. Check conservation, analytical references,
and refinement together. Do not compute phase from `T` or fill masked phases
through an unresolved zero of `t`.

<a id="eq-s8"></a>
## S8. An independent continuum rectangular-barrier benchmark

Assume identical zero-potential continuum leads, positive `E`, constant mass,
a rectangular barrier of height $V_b\geq0$ and width `d>0`, and plane separation
$L\geq d$. In this section $k=\sqrt{2m^*E}/\hbar$ and
$p=\sqrt{2m^*(E-V_b)}/\hbar$ are inverse lengths; below the barrier choose $p=i\kappa$
with `κ>0`. All energies and lengths use mutually consistent units.

In the barrier, the ODE is $\chi''+p^2\chi=0$. Its exact fundamental solutions give

$$
\begin{pmatrix}\chi(d)\\\chi'(d)\end{pmatrix}
=\begin{pmatrix}\cos(pd)&\sin(pd)/p\\-p\sin(pd)&\cos(pd)\end{pmatrix}
\begin{pmatrix}\chi(0)\\\chi'(0)\end{pmatrix}.
$$

The upper-right entry has length units, the lower-left inverse-length units,
and each row has the correct units for `χ` or `χ'`. This matrix is an analytical
matching device here, not the production propagation algorithm. At the barrier
faces set $\chi(0)=1+r_b$, $\chi'(0)=ik(1-r_b)$, $\chi(d)=t_b$, and $\chi'(d)=ikt_b$.
Using the inverse matrix, add $\chi(0)+\chi'(0)/(ik)=2$ to eliminate `r_b`. This yields

$$
t(E)=\frac{e^{ik(L-d)}}{\cos(pd)-i\frac{k^2+p^2}{2kp}\sin(pd)}.
$$

The dimensionless prefactor supplies free padding and makes this phase agree
with S4. For $E=V_b>0$, take the limit $\sin(pd)/p\to d$, giving the denominator
$1-ikd/2$. Squaring the magnitude and simplifying separately on each side gives

$$
T(E)=
\begin{cases}
\left[1+\dfrac{V_b^2\sinh^2(\kappa d)}{4E(V_b-E)}\right]^{-1},&0<E<V_b,\\
\left[1+\dfrac{m^*V_b d^2}{2\hbar^2}\right]^{-1},&E=V_b>0,\\
\left[1+\dfrac{V_b^2\sin^2(pd)}{4E(E-V_b)}\right]^{-1},&E>V_b.
\end{cases}
$$

This is a continuum benchmark, not the exact finite-grid answer. qwave's
`rectangular_probability` is coded separately from its complex analytical
amplitude, and both are independent of the production solver. The reference
amplitude uses scaled decaying exponentials below the barrier to avoid
hyperbolic overflow. A separate ODE matching reference checks smooth moderate
barriers; it is not trusted for extremely opaque fundamental matrices.

## What convergence should establish

Notebook 1 keeps physical dimensions and energies fixed, samples the barrier
with the library's declared cell-average convention, refines spacing, and
records errors in **complex `t`**, `T`, and conservation. A free channel also
has a finite-grid phase error relative to continuum $\exp(ikL)$. Conservation
can be excellent on a coarse lattice while its dispersion is inaccurate.

Smooth-potential central differences have second-order local truncation error
under regularity assumptions; observed global convergence at steps or narrow
resonances must be measured. Tolerances in tests come from those benchmark
scales and floating-point behavior, not from a new physical law. Even a
converged calculation only solves the assumed effective-mass model.
