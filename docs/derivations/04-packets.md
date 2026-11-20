# 4. Energy packets, transmission, and conditional fidelity

Prerequisites: the current and phase conventions of Chapters 2–3. We introduce
the Fourier normalization and change-of-variable rule before constructing a
physical position density. `t(E)` below is transmission amplitude; observation
time is always written `t_obs`.

<a id="eq-p1"></a>
## P1. From a sum of waves to an integral

On an infinite uniform lead, use the right-going branch `k>0`. A continuum lead
has no upper `k` limit; the finite-difference lead uses `0<k<π/a`. Let `a_k(k)`
be a wave-number amplitude, of units `sqrt(length)`, supported inside the
selected branch. With energy `E(k)` and the time sign of S1, set

$$
\Psi(x,t_{\rm obs})=\frac{1}{\sqrt{2\pi}}\int a_k(k)
 e^{ik(x-x_0)-iE(k)t_{\rm obs}/\hbar}\,dk.
$$

`x,x_0` have length units. The wavefunction has units `length^(-1/2)`.
This Fourier integral is a coherent sum: add complex amplitudes before
squaring. Its full-line normalization follows from Fourier orthogonality.
The shorthand

$$
\int_{-\infty}^{\infty}e^{i(k-k')x}\,dx=2\pi\delta(k-k')
$$

is a **distributional identity**, not a convergent ordinary improper integral.
The delta is defined by its action under integration,
$\int\delta(k-k')f(k')\,dk'=f(k)$ for suitable test functions; it has length units here.
One can first prove Fourier norm preservation for smooth, rapidly decaying
functions, then extend it by limits to square-integrable spectra. Applying
that theorem to P1 gives

$$
\int_{\mathbb R}|\Psi|^2\,dx=\int |a_k(k)|^2\,dk.
$$

Thus normalizing the spectrum normalizes this uniform-lead packet. For a
discrete lead, P1 is the band-limited continuous interpolation; at lattice
points the corresponding full infinite-lattice norm is also
$a\sum_n|\Psi(x_0+na)|^2$. These are ideal full-domain statements, not guarantees
that a finite plotted window captures the whole packet.

<a id="eq-p2"></a>
## P2. Energy normalization and its Jacobian

On the monotone positive-speed branch, S5 (or the continuum dispersion) gives
$dE/dk=\hbar v(E)>0$. A Jacobian is the derivative converting one integration
variable to another. Requiring equal probability in corresponding intervals,

$$
|a_k(k)|^2\,dk=|A(E)|^2\,dE,\qquad
a_k(k)=\sqrt{\hbar v(E(k))}\,A(E(k)),
$$

defines a consistent phase convention for the energy amplitude `A`. Its units
are `energy^(-1/2)`. Substitute $dk=dE/(\hbar v)$ in P1 to obtain

$$
\Psi(x,t_{\rm obs})=\int A(E)
 \frac{e^{ik(E)(x-x_0)-iEt_{\rm obs}/\hbar}}{\sqrt{2\pi\hbar v(E)}}\,dE.
$$

The basis function has units `(energy × length)^(-1/2)` and is delta-normalized
in energy. It is the unit-flux spatial basis of S4 divided by $\sqrt{2\pi\hbar}$.
This is why simply Fourier-transforming `A(E)` with an `Ex` phase is wrong:
energy is not inverse length, `k(E)` is nonlinear, and the velocity factor is
required. In nm/meV/ps units use `ħ` in meV ps and `v` in nm/ps; convert the
solver's m/s velocity by multiplying by `10^-3`.

For the full static scattering problem, superpose the corresponding
left-incident stationary states with these energy-normalized coefficients.
The prepared incoming scattering packet has unit norm when $\int|A|^2\,dE=1$.
Its asymptotic reflected and transmitted components use `A r` and `A t` in
their respective outgoing bases. Possible bound states are not added to an
incoming packet prepared in the scattering subspace. P2 describes a lead
component, not an interior scattering wavefunction or a finite-time division
of all probability between arbitrary spatial boxes.

<a id="eq-p3"></a>
## P3. A restricted Gaussian is an amplitude, not a density

Let the desired central energy be `E_c` and untruncated **probability-density**
standard deviation be `σ_E>0`, both in meV. Let $W=[E_{\min},E_{\max}]$ be a finite
energy window strictly inside the common open lead band. On this window,

$$
\rho_0(E)=\frac{1}{\sqrt{2\pi}\sigma_E}
 e^{-(E-E_c)^2/(2\sigma_E^2)},\qquad
Z_W=\int_W\rho_0(E)\,dE,\qquad
A(E)=\frac{\sqrt{\rho_0(E)}}{\sqrt{Z_W}}.
$$

Outside `W`, set $A=0$; an optional declared spectral phase can multiply it
without changing its density. `ρ_0` has units `meV^-1`, `A` has units
`meV^(-1/2)`, and `Z_W` is dimensionless. The amplitude exponent has denominator
`4σ_E²`, not `2σ_E²`. After truncation the actual mean and standard deviation
need not equal `E_c,σ_E`.

`gaussian_packet` uses positive trapezoidal weights to compute the sampled
normalization and records the analytic Gaussian CDF masses in the full common
band and the chosen window. It requires the center inside the window and a
resolved energy grid. Renormalization does **not** turn omitted tails into
reflection. It defines a restricted incoming state. Refining the grid tests
quadrature error; enlarging the window tests truncation error. They are
different studies.

<a id="eq-p4"></a>
## P4. Throughput and the normalized output state

On `W`, use the energy amplitude `A` normalized as above and flux transmission
`t(E)` from S4. The unnormalized transmitted spectral state and its probability
are

$$
B(E)=A(E)t(E),\qquad
P_{\rm trans}=\|B\|_W^2=\int_W |A(E)|^2|t(E)|^2\,dE.
$$

`B` has units `meV^(-1/2)` and `P_trans` is dimensionless. This follows from the
energy-basis orthogonality in P2, not from treating components as classical
trajectories. Energy is conserved by the static model, so scattering does not
mix different energies. With both lossless open channels, the corresponding
reflection integral sums with `P_trans` to one. It is an asymptotic statement.

For `P_trans>0`, define the **conditional** transmitted state

$$
g(E)=\frac{B(E)}{\sqrt{P_{\rm trans}}}.
$$

Its norm is one and its units remain `meV^(-1/2)`. Conditioning asks about the
state **given transmission**. It cannot tell how frequently transmission
occurs. At zero or numerically unnormalizable throughput this state is
undefined. At small positive throughput it may be computable, but its low
probability must remain flagged and reported.

<a id="eq-p5"></a>
## P5. Fidelity to a declared target

Choose a target amplitude `t_ref(E)` for the same incident state and phase
planes, for example the clean device or the free reference channel. Define
$B_{\rm ref}=At_{\rm ref}$, $P_{\rm ref}=\int|B_{\rm ref}|^2\,dE>0$, and $h=B_{\rm ref}/\sqrt{P_{\rm ref}}$. The raw
conditional fidelity is

$$
F_{\rm raw}=|\langle h,g\rangle_W|^2
=\frac{\left|\int_W |A(E)|^2\,t_{\rm ref}(E)^*t(E)\,dE\right|^2}
 {P_{\rm ref}P_{\rm trans}}.
$$

Every factor is dimensionless after integration; the star belongs on the
reference in this convention. Cauchy–Schwarz gives $0\leq F_{\rm raw}\leq1$. Exchanging
the two states conjugates the overlap and leaves fidelity unchanged, but
incorrectly conjugating neither generally changes it.

If $t=ct_{\rm ref}$ with a constant nonzero complex `c` consistent with elastic
probability bounds, the output is just a global phase times the target after
normalization: fidelity is one while throughput is `|c|²P_ref`. In particular,
a nearly opaque channel can have excellent conditional fidelity. P4 and P5
must always be displayed together. An integral of `|A|²T` is P4, never a fidelity.

<a id="eq-p6"></a>
## P6. Delay alignment with a sign and a finite search interval

Under $\exp(-iEt_{\rm obs}/\hbar)$, multiplying a spectrum by $\exp(+iE\delta/\hbar)$ shifts its
time dependence to `t_obs-δ`: positive `δ` is a lag. A declared alignment lag
`s` therefore removes the factor using a **minus** sign:

$$
F(s)=\left|\int_W h(E)^*g(E)
 e^{-i(E-E_p)s/\hbar}\,dE\right|^2,\qquad
\widehat s\in\underset{s\in[s_{\min},s_{\max}]}{\operatorname{argmax}}F(s).
$$

Here `s,s_min,s_max` are in ps, `E_p` is an arbitrary fixed pivot energy in meV,
and `ħ` is in meV ps. The pivot contributes only a global phase and changes no
fidelity. Bounds must include zero to retain the raw comparison. The code
scans a declared finite grid, includes endpoints, and refines observed local
maxima with bounded scalar optimization. It reports the lag, bounds, sample
count, boundary status, and raw fidelity. This is a finite numerical search,
not a certificate of a continuous global maximum for an arbitrarily oscillatory
spectrum. A flat scan has no uniquely estimated lag.

Both the energy quadrature and delay scan must resolve the largest allowed
phase variation. Unlimited alignment could hide arrival-time changes that
matter. Alignment leaves `P_trans` unchanged and is an optional diagnostic,
not a replacement target chosen after viewing results.

<a id="eq-p7"></a>
## P7. Synthetic analytical checks, explicitly separate from devices

For these checks only, assume a Gaussian on the **entire real energy line**, a
constant reference amplitude, and formal multiplicative transformations. This
is a mathematical approximation to a wide-window, well-above-threshold packet,
not a physical lead spectrum at negative energies. To derive the linear-phase
integral, set `Y=E-E_c` and let `I(b)` denote the integral below. This expectation
of a complex phase is called a characteristic function. Differentiation under
the integral is permitted by the Gaussian's integrable moments. Since
$\rho_0'(E)=-(E-E_c)\rho_0(E)/\sigma_E^2$, integration by parts, with vanishing
Gaussian boundary terms, gives $I'(b)=-\sigma_E^2b I(b)$. The initial condition
is $I(0)=1$. Solving this first-order ODE gives

$$
\int_{\mathbb R}\rho_0(E)e^{ib(E-E_c)}\,dE
=e^{-\sigma_E^2b^2/2},\qquad
F_{\rm raw}(\delta)=e^{-\sigma_E^2\delta^2/\hbar^2}.
$$

`b` has units `meV^-1`; the second equality uses $b=\delta/\hbar$ for a pure delay.
If the allowed lag interval contains `δ`, perfect alignment gives one in the
continuum integral. A constant global phase instead gives raw fidelity one.

For a quadratic phase $\exp(i\beta(E-E_c)^2)$ with real `β` in `meV^-2`, set
$Q(\beta)=\mathbb E[\exp(i\beta Y^2)]$. The same integration-by-parts identity
applied to $Y\exp(i\beta Y^2)$ gives
$Q'(\beta)=i\sigma_E^2 Q(\beta)/(1-2i\beta\sigma_E^2)$ with $Q(0)=1$.
Consequently $Q=(1-2i\beta\sigma_E^2)^{-1/2}$, choosing the square-root branch
continuous from one at zero. Squaring its magnitude gives

$$
F_{\rm raw}=\left(1+4\beta^2\sigma_E^4\right)^{-1/2},\qquad P_{\rm trans}=1.
$$

For an amplitude filter $\exp(-(E-E_c)^2/(4b_E^2))$, where `b_E>0` is in meV,
define the dimensionless ratio $q=\sigma_E^2/b_E^2$. Direct Gaussian integration gives

$$
P_{\rm trans}=(1+q)^{-1/2},\qquad
F_{\rm raw}=\frac{\sqrt{1+q}}{1+q/2}.
$$

The denominators come respectively from the norm of the filtered amplitude
and the squared overlap divided by that norm. These exact full-Gaussian
identities have finite-window corrections in the notebook. Its configurations
record omitted tail mass and numerical refinement; disagreement beyond those
scales is a failed check, not a new effect.

<a id="eq-p8"></a>
## P8. What the plotted packet actually means

`reconstruct_lead_packet` applies P2 with `A` replaced by $B=At$ in the
outgoing lead, $x_0=x_R$, and the exact discrete `k(E),v(E)`. It may subtract a
carrier energy from the time phase, which changes only a common phase and
not the position density. No spatial renormalization is applied.

The full-line ideal norm of this lead continuation is `P_trans`; a finite
display window can contain less. The continuation to points inside or to the
left of the device is **not** the interior solution. A plot restricted to the
right lead is a plotted outgoing component, not a full evolving scattering
state at early times. State which component and window are being shown.

A finite energy quadrature produces a finite sum of plane waves. Extending
that finite sum to the entire real line would not be square integrable.
Consequently, compare its norm on a fixed, resolved spatial window while
refining energy spacing, then check window enlargement before quadrature
recurrences dominate. Position spacing must resolve the largest wave number.
The notebook saves spatial densities in `nm^-1`, spectral densities in
`meV^-1`, both finite-window norms, and quadrature settings. No plotted curve
is called an electron trajectory.
