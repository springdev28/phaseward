# 2. An assumed quantum model and its conserved current

Prerequisite: Chapter 1's complex arithmetic, partial derivatives, inner product,
and product rule. We now introduce a physical model; classical mechanics does
not logically force this equation.

<a id="eq-s1"></a>
## S1. The model postulate

On the real line, assume a coherent single electron with constant effective
mass `m*>0`, a real time-independent potential energy `V(x)`, and complex
wavefunction `Ψ(x,t_obs)`. In SI, `x` is m, observation time `t_obs` is s,
`m*` is kg, `V` is J, and `Ψ` has units `m^(-1/2)`. The model is

$$
i\hbar\frac{\partial\Psi}{\partial t_{\rm obs}}
=-\frac{\hbar^2}{2m^*}\frac{\partial^2\Psi}{\partial x^2}+V(x)\Psi.
$$

Both sides have units energy × wavefunction. We interpret `|Ψ|²` as position
probability density and normalize a single packet over the full line. This
interpretation is also a physical assumption. The kinetic term is a second
spatial derivative; a PDE needs a suitable initial state and boundary behavior.
For the continuum manipulations below, assume enough smoothness and decay for
the derivatives and integrations; finite steps in `V` can be handled piecewise
with matching conditions.

`m*` summarizes an idealized effective-mass description. The examples' ratio
$m^*/m_e=0.067$ is illustrative and configurable, not a universal electron mass
in semiconductors. The model ignores spin dynamics, inelastic interactions,
many-electron effects, and decoherence. Gate parameters are **potential
energies** in meV. Inferring electrode voltage requires a separate
electrostatic model that is not supplied.

Linearity means a sum of solutions with fixed coefficients is another solution
for the same prescribed `V`. This is why we can later assemble stationary
solutions into a packet. It is not a statement that probabilities add without
interference.

<a id="eq-s2"></a>
## S2. Deriving the continuity equation, including the sign

Use the assumptions and SI units of S1. Define density $\rho_x=\Psi^*\Psi$ (unit `m^-1`).
Solve S1 for the time derivative and conjugate it:

$$
\partial_{t_{\rm obs}}\Psi=
\frac{i\hbar}{2m^*}\Psi''-\frac{iV}{\hbar}\Psi,\qquad
\partial_{t_{\rm obs}}\Psi^*=
-\frac{i\hbar}{2m^*}\Psi^{*\prime\prime}+\frac{iV}{\hbar}\Psi^*.
$$

Primes mean spatial derivatives, not time derivatives. Applying the product
rule cancels the two real-potential terms:

$$
\partial_{t_{\rm obs}}\rho_x
=\frac{i\hbar}{2m^*}(\Psi^*\Psi''-\Psi\Psi^{*\prime\prime})
=-\partial_x j,\qquad
j=\frac{\hbar}{2m^*i}(\Psi^*\Psi'-\Psi\Psi^{*\prime})
=\frac{\hbar}{m^*}\operatorname{Im}(\Psi^*\Psi').
$$

`j` is probability current, with units `s^-1` in one dimension. It is a signed
rate across a point, not a probability density. For fixed endpoints `a<b`,

$$
\frac{d}{dt_{\rm obs}}\int_a^b\rho_x\,dx=j(a,t_{\rm obs})-j(b,t_{\rm obs}).
$$

The probability inside increases by inflow minus outflow. If current vanishes
at both infinities for a normalizable packet, total probability stays one. A
complex absorptive potential would add a source/sink term; that would be a
different model and cannot be inserted into this conservation proof.

As a sign check, take a plane wave of coefficient `c` and positive wave number
`k`, proportional to $\exp(ikx-iEt_{\rm obs}/\hbar)$. In S2 the spatial derivative is
`ik` times the wave; hence its current is `ħk|c|²/m*>0`. Reversing `k` reverses
current. The plane wave itself extends infinitely and has no finite norm.

<a id="eq-s3"></a>
## S3. Stationary states by separation of variables

For a static potential, try a solution $\Psi=\chi_E(x)\exp(-iEt_{\rm obs}/\hbar)$, where real
`E` is energy in J and `χ_E` is a stationary spatial amplitude. Substituting,
then canceling the nonzero time factor, gives

$$
-\frac{\hbar^2}{2m^*}\chi_E''(x)+V(x)\chi_E(x)=E\chi_E(x).
$$

This is a second-order ordinary differential equation in space, not a
classical trajectory equation. The time factor changes phase but not the
density of one stationary solution. For a constant lead potential `V_ell`
and an open channel `E>V_ell`, its two independent solutions and speed are

$$
\chi_E(x)=c_+e^{ik_\ell x}+c_-e^{-ik_\ell x},\qquad
k_\ell=\frac{\sqrt{2m^*(E-V_\ell)}}{\hbar},\qquad
v_\ell=\frac{\hbar k_\ell}{m^*}.
$$

The lead index `ell` denotes left or right; `k_ell` is positive with units
`m^-1`, `v_ell` has units m/s, and `c_±` carry the spatial amplitude's units.
For `E<V_ell` the wave number is imaginary and solutions are exponential;
they are not propagating channels with positive speed. At a finite jump in
`V` with **constant mass and no delta-function potential**, integrate S3 over
a shrinking interval to obtain continuous `χ_E'`; `χ_E` is also continuous.
Different masses or singular potentials require different matching rules.

We solve incoming scattering states, not bound-state eigenvalues. Their boundary
conditions impose a specified incident wave, a reflected outgoing wave in the
left lead, and a transmitted outgoing wave in the right lead. They are not
square-integrable states individually. Chapter 4 supplies normalizable packets.

## A first physical interpretation

An electron described by this model does not have a literal classical path
drawn by the wavefunction. Repeated position measurements on equally prepared
packets are modeled by the density. Transmission probabilities describe
asymptotic channel outcomes; a complex transmission amplitude also carries
phase information needed to reconstruct interference and packet shapes.

The passage from the stationary ODE to the finite-difference model in Chapter 3
is a **numerical approximation** to S1. We derive its lead dispersion explicitly
so the continuum and discrete currents never get mixed.
