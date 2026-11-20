# 7. A sensitivity objective, constrained design, and limits of inference

Prerequisites: the packet inner product, Gaussian covariance coefficients, and
complex derivatives. The sensitivity objective is an **experimental surrogate**.
This chapter derives what it measures and gives explicit reasons it need not
minimize fidelity loss, a failure probability, or a real device's risk.

<a id="eq-o1"></a>
## O1. An expectation of a linearized squared change

Fix an energy window `W` (meV), real gate vector `u` (meV), retained covariance
eigenvalues `λ_k` (`meV² nm`), and derivatives `D_k` from L1. Let $w(E)\geq0$ be
a density in `meV^-1` normalized by $\int_W w\,dE=1$. The default is the incoming
energy probability density `|A(E)|²`; the alternative uniform importance is
`1/(E_max-E_min)`. These are declared choices, not fitted to held-out outcomes.

By L4 and nonnegativity (so expectation and integration can be interchanged),

$$
J(u)=\sum_{k=1}^K\lambda_k\int_W w(E)|D_k(E;u)|^2\,dE
=\mathbb E_{\rm ens}\!\left[\int_W w(E)|\delta t_{\rm lin}(E;u)|^2\,dE\right].
$$

`J` is dimensionless. When $w=|A|^2$, it equals the expected squared norm of
the **unnormalized, first-order transmitted-packet change** `A δt_lin`.
Uniform importance instead measures a different spectral weighting and does
not have that incoming-packet interpretation unless its density is uniform.

If coordinates are changed to unit-variance `z_k` with
$\eta_k=\sqrt{\lambda_k}z_k$, the chain rule gives

$$
\frac{\partial t}{\partial z_k}=\sqrt{\lambda_k}D_k,\qquad
J=\sum_k\int_W w(E)\left|\frac{\partial t}{\partial z_k}\right|^2\,dE.
$$

Here the `z` derivative is dimensionless. These are equivalent conventions;
applying another `λ_k` weight to a `z` derivative is not. The code and saved
data consistently use the `η` convention. Orthogonal changes of basis within
a retained degenerate covariance eigenspace leave the summed objective
unchanged even though individual plotted mode sensitivities change.

For nonzero nominal disorder scale `σ` in meV, the optional quantity
$J_{\rm normalized}=J/\sigma^2$ has units `meV^-2`. At fixed covariance shape and retained
subspace, `λ_k` scale as `σ²`, so this removes that amplitude factor from the
linear surrogate. It does not remove energy/grid error, mode omission,
nonlinearity, or the nominal physical disorder scale. Both quantities are
reported; neither is a probability or a fidelity.

<a id="eq-o2"></a>
## O2. Why this is not the same as conditional fidelity

Use the energy inner product of P5 with default packet weighting. Take a
nonzero clean target $B_0=At_0$, with norm squared `P_0`, normalized state
$h=B_0/\sqrt{P_0}$, and exact perturbed output $B=B_0+\delta B$ of norm squared `P>0`.
Let $\Pi f=h\langle h,f\rangle$ project any spectrum onto the target direction and `I` be the
identity operator. To verify orthogonality, use unit norm of `h` in
$\langle h,f-h\langle h,f\rangle\rangle=0$; `f` is any square-integrable energy
amplitude with the same units as `h`. Expanding the squared norm then gives
the exact identity

$$
1-F=\frac{\|(I-\Pi)B\|^2}{P}
=\frac{\|(I-\Pi)\delta B\|^2}{P}
\leq\frac{\|\delta B\|^2}{P}.
$$

All norms integrate over energy and are dimensionless. This assumes the
target is **this clean output**, not an unrelated reference. The inequality
follows because orthogonal projection cannot increase norm. It is exact for
the full state difference, regardless of a Taylor approximation.

For $\delta B=\varepsilon b_1+O(\varepsilon^2)$ in norm, with dimensionless small real `ε`, fixed
`P_0>0`, and adequate smoothness, the leading conditional infidelity is

$$
1-F=\frac{\varepsilon^2}{P_0}
\left(\|b_1\|^2-|\langle h,b_1\rangle|^2\right)+O(\varepsilon^3).
$$

`b_1` has units `meV^(-1/2)`. The target-parallel part of the first-order
change does **not** contribute to this leading infidelity. The surrogate
counts both parallel and orthogonal changes, and does not divide by the
actual transmitted norm. It is consequently a different objective.

For an explicit synthetic counterexample, let a dimensionless random real
variable `ζ` have zero mean and variance `s_ζ²`, and define
$t(E;\zeta)=\exp(ic\zeta)t_0(E)$ with real dimensionless constant `c`. Every
realization has the same throughput and conditional fidelity one, yet its
first-order complex-change objective is

$$
J_{\rm phase}=c^2s_\zeta^2\int_W w(E)|t_0(E)|^2\,dE.
$$

This is positive when the stated factors are nonzero. It is a mathematical
family illustrating the metric distinction, **not** a claim that a particular
electrostatic gate produces exactly this transformation. Notebook 4 uses
`analyze_packet` to check the fidelity claim. Energy-dependent phase can
instead change raw fidelity; a bounded delay may remove only its appropriate
linear-in-energy part. Thus alignment changes the diagnostic, not O1's meaning.

<a id="eq-o3"></a>
## O3. What a probability bound would actually require

For the same exact states as O2, Cauchy–Schwarz also gives

$$
|P-P_0|\leq2\sqrt{P_0}\,\|\delta B\|+\|\delta B\|^2.
$$

If a design guaranteed $P\geq p_{\min}>0$ for **all evaluated draws**, O2 would imply
$\mathbb E_{\rm ens}[1-F]\leq\mathbb E_{\rm ens}[\|\delta B\|^2]/p_{\min}$. This needs an exact full-response mean-square
bound and the correct target. A constraint on clean throughput alone does
not supply the premise, and the first-order `J` is not that exact expectation.

To see the limited role of a surrogate tail bound, define the nonnegative
dimensionless variable $X_{\rm lin}=\|A\delta t_{\rm lin}\|^2$ with default weighting. Markov's
inequality (integrate $X\geq a$ over the event $X\geq a$) gives for `a>0`

$$
\Pr(X_{\rm lin}\geq a)\leq\frac{J}{a}.
$$

This is a bound for a particular **linearized norm event** under the specified
coefficient distribution; it can be very loose. It is not the probability of
low transmitted current, poor fidelity, fabrication failure, or experimental
failure. To connect it with those events one would need controlled Taylor and
KL errors, throughput bounds, appropriate event definitions, and a validated
physical distribution. None is supplied merely by minimizing `J`.

<a id="eq-o4"></a>
## O4. Feasible design before objective ranking

The user chooses gate bounds and target before optimization. In a typical
configuration the finite gate vector `u∈R^M` must satisfy

$$
P_{\rm clean}(u)\geq P_{\min},\qquad
F_{\rm clean,raw}(u)\geq F_{\min},\qquad
u_j^{\min}\leq u_j\leq u_j^{\max},\qquad
\max_x\left|\sum_j u_jg_j(x)\right|\leq V_{\max}.
$$

Probabilities, fidelities, and their floors are dimensionless; gate coefficients
and `V_max` are in meV. The maximum is over saved channel/grid samples in the
implemented constraint, not a certified bound between every interpolation
point. An optional sampled spatial-gradient bound is in meV/nm. Positive raw
constraint residuals denote feasibility within the declared numerical
tolerances. Undefined fidelity cannot be treated as a feasible high-fidelity
state. These clean constraints prevent obvious opaque solutions but do not
guarantee disordered performance.

The optimization problem is to minimize a scalar objective over that feasible
set. SLSQP is a local numerical method using local approximations and
constraints; multiple common initializations improve exploration but do not
prove a global optimum. Gate-gradient finite differences need their own
step-size checks even when `dt/dV` comes from an implicit response solve.
The library saves failures, infeasible trials, stopping reasons, and costs.

Compare fixed gates, clean-state optimization, direct Monte Carlo robust
optimization, and this sensitivity objective with the same gate controls and
work caps. Keep training, development, and final held-out seeds disjoint;
freeze designs before drawing or reading final evaluations. Do not retune the
objective or select a design after inspecting its held-out score. Report
paired distributions, uncertainty, throughput, fidelity, and computational
cost even when the candidate performs worse.

## What these derivations establish

They establish normalization identities and a precisely defined surrogate for
the declared model. They leave open whether the surrogate improves held-out
performance under any particular design and resource budget. Narrow resonances,
low throughput, omitted modes, inaccurate derivatives, energy quadrature,
ill-conditioned solves, distribution mismatch, and missing physics can all
break an inference from small `J` to useful transport. A successful notebook is
a mathematical and software verification, not confirmation of a robustness
hypothesis or a laboratory observation.
