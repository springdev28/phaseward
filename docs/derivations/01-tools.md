# 1. Mathematical tools, with units attached

Read this chapter before the physics. The symbols below describe mathematics;
they acquire physical meanings only when the next chapters declare them.

<a id="eq-m1"></a>
## M1. Derivatives, integrals, and local approximation

Let `f` be a real or complex function of a real coordinate `x` on an interval,
with units `U` for its value and length `L` for its argument. A derivative is a
local rate of change, and an integral is a limit of weighted sums:

$$
f'(x)=\lim_{h\to0}\frac{f(x+h)-f(x)}{h},\qquad
\int_a^b f(x)\,dx=\lim_{\max\Delta x_j\to0}\sum_j f(\xi_j)\Delta x_j.
$$

Here `h`, endpoints `a,b`, points `ξ_j`, and widths `Δx_j` have units `L`;
`f'` has units `U/L` and the integral has units `UL`. The derivative requires
differentiability, the displayed sum requires an integrable function and a
refining partition. A complex derivative with a **real** argument differentiates
its real and imaginary parts separately.

For three continuous derivatives near `x`, Taylor's theorem gives

$$
f(x+h)=f(x)+hf'(x)+\frac{h^2}{2}f''(x)+O(h^3).
$$

The remainder notation means its magnitude is bounded by a constant times
`|h|³` locally; the constant carries the needed units. It is not a declaration
that a finite step is small enough. Subtracting the expansions at positive and
negative `h` cancels the even terms. Chapter 6 turns that observation into a
derivative diagnostic with roundoff error as well as truncation error.

For a function `f(x,t_obs)` of two independent variables, a **partial derivative**
holds the other argument fixed. For example, `∂f/∂t_obs` changes observation time
at a fixed position. A differential equation containing these partial
derivatives is a PDE. Initial data specify a state at a time; boundary data
specify allowed behavior at spatial boundaries. They are different information.

<a id="eq-m2"></a>
## M2. Complex numbers carry phase

For real numbers `a,b` with common units `U`, define $z=a+ib$, where $i^2=-1$.
Conjugation reverses the imaginary part. For dimensionless real angle `θ`,

$$
z^*=a-ib,\qquad |z|^2=z^*z=a^2+b^2,\qquad
e^{i\theta}=\cos\theta+i\sin\theta,\qquad (zw)^*=z^*w^*.
$$

`|z|²` has units `U²`; a phase angle is dimensionless. Conjugation also changes
`i` to `-i` in a differential equation. A real probability discards phase:
many complex numbers have the same squared magnitude. Taking a square root of
a probability cannot recover a scattering phase.

A derivative or integral of complex values uses ordinary real calculus on both
parts. For differentiable `z(s)` with real parameter `s`, the product rule yields

$$
\frac{d|z|^2}{ds}=2\operatorname{Re}\!\left(z^*\frac{dz}{ds}\right).
$$

`s` may have any declared unit, so both sides have units `U²/[s]`. The star is
essential: this identity is generally false with `z` instead of `z*`.

<a id="eq-m3"></a>
## M3. Amplitudes, densities, and weighted inner products

Let `y` have unit `Y` on a domain `D`, and let functions `f,g` be square
integrable with units `Y^(-1/2)`. Define the inner product and squared norm by

$$
\langle f,g\rangle_D=\int_D f(y)^*g(y)\,dy,\qquad
\|f\|_D^2=\langle f,f\rangle_D.
$$

Both are dimensionless. The first slot is conjugated, so
$\langle g,f\rangle=\langle f,g\rangle^*$. A normalized amplitude has norm one. Its squared magnitude is a
density with units `1/Y`; integration over a set gives a dimensionless
probability. Densities in position and energy are different functions and have
different units. Density values need not be less than one.

The Cauchy–Schwarz inequality and its proof will be useful:

$$
|\langle g,f\rangle|^2\leq\|g\|^2\|f\|^2,\qquad
0\leq\left\|f-\frac{\langle g,f\rangle}{\|g\|^2}g\right\|^2
=\|f\|^2-\frac{|\langle g,f\rangle|^2}{\|g\|^2}.
$$

The proof assumes `g` has nonzero finite norm and expands the square using the
conjugate convention; the zero vector case is immediate. Thus the squared
overlap of normalized states lies between zero and one. This is an overlap of
amplitudes, not an overlap of their probability densities.

On increasing nodes `y_j`, trapezoidal quadrature uses endpoint half-interval
weights and interior adjacent-half-interval sums. Writing these positive
weights as `w_j` (unit `Y`) gives

$$
\langle f,g\rangle_{\rm quad}=\sum_j w_j f_j^*g_j.
$$

This is an exact finite-dimensional inner product on the sampled vectors;
its agreement with the continuum integral still needs refinement. Positive
weights preserve positivity and Cauchy–Schwarz. Ordinary `sum(abs(f)**2)` is not
the same normalization. `qwave.wavepackets.quadrature_weights` implements these
weights, including nonuniform increasing grids.

<a id="eq-m4"></a>
## M4. Matrices, eigenvectors, and what a transpose means

A vector is an ordered set of components; a matrix is a linear map between
vectors. Matrix multiplication sums a row against a column. `I` denotes the
identity map. For a matrix `A`, `A^T` exchanges its indices; $A^\dagger=(A^*)^T$ also
conjugates. They coincide only for real matrices. An inverse solves a linear
system when it exists; software should usually **solve** the system instead of
forming an inverse.

For an `n` by `n` Hermitian matrix $H=H^\dagger$, the spectral theorem states

$$
H=Q\Lambda Q^\dagger,\qquad Q^\dagger Q=I,\qquad
Hq_k=\lambda_k q_k.
$$

`q_k` is column `k` of `Q`, an eigenvector; `Λ` is diagonal with real
eigenvalues `λ_k`. If `H` has unit `U`, normalized `q_k` and `Q` are
dimensionless and `λ_k` has unit `U`. The theorem is exact in finite dimensions;
numerical eigenvectors have roundoff error. A real symmetric matrix admits
real orthonormal eigenvectors. Its eigenvectors need not be unique within a
repeated-eigenvalue subspace.

Positive semidefinite means $a^\dagger Ha\geq0$ for every complex dimensionless vector
`a`. By the decomposition, this is equivalent to nonnegative eigenvalues.
Covariance matrices have this property. A spatial quadrature changes what
“normalized” means; Chapter 5 derives the required weighted eigenproblem.

The matrices defining open scattering boundaries are generally **not**
Hermitian after the infinite leads have been eliminated. A theorem for
Hermitian matrices cannot silently be applied to them.

## Units and approximations as part of a formula

Public lengths are nm, energies are meV, and packet times are ps. One nm is
`10^(-9)` m, one ps is `10^(-12)` s, and one meV is `10^(-3)` times the elementary
charge in joules. `ħ` is Planck's constant divided by `2π`, an action with units
energy × time. The package obtains physical constants from SciPy and performs
the scattering calculation with explicit SI conversions. Never mix a velocity
in m/s with a length in nm in the same phase or Jacobian expression.

An equality can be exact **within an assumed discrete model** without being an
exact continuum or laboratory statement. Keep five separate error sources:

1. Physical-model omission: a real device may not obey the assumptions.
2. Numerical discretization: finite spatial/energy grids and finite windows.
3. Representation truncation: discarded disorder modes.
4. Approximation: omitting nonlinear Taylor terms.
5. Sampling uncertainty: finitely many random realizations.

Roundoff and ill-conditioned solves add numerical error even on a fixed grid.
Convergence studies isolate one source at a time instead of attributing all
changes to physics.

## Checks before continuing

If `z=1+i`, `z*z=2i` but `z.conjugate()*z=2`. Which is a squared magnitude?
If an energy amplitude has unit `meV^(-1/2)`, its density has unit `meV^(-1)`.
If the same density is expressed per eV, its numerical values change while
integrated probabilities stay the same. These are algebra and unit checks,
not numerical transport results.

