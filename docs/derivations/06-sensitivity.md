# 6. First-order changes of a complex transmission amplitude

Prerequisites: Taylor's theorem, matrix solves, flux amplitudes, and the weighted
KL convention. Fix energy, gate settings, effective mass, grids, and both lead
potentials. Only real channel-potential coefficients change. We differentiate
the **complex amplitude**, before taking magnitudes or unwrapping any phase.

<a id="eq-l1"></a>
## L1. Multivariable Taylor expansion with real coefficients

At each allowed energy `E`, view `t(E;u,η)` as a complex function of `K` real
coordinates `η_k` (units `meV sqrt(nm)`). Write $t=t_{\rm Re}+it_{\rm Im}$; ordinary real
multivariable calculus applies to each part. Define

$$
D_k(E;u)=\left.\frac{\partial t(E;u,\eta)}{\partial\eta_k}\right|_{\eta=0},
\qquad
t(E;u,\eta)=t_0(E;u)+\sum_{k=1}^K D_k(E;u)\eta_k+\mathcal R(E;u,\eta).
$$

$t_0=t(E;u,0)$ and the remainder `R` are dimensionless complex numbers;
`D_k` has units `(meV sqrt(nm))^-1`. The expansion requires differentiability
of the scattering response in a neighborhood, with a nonsingular boundary
matrix. Smooth matrix entries alone do not guarantee a small response near an
ill-conditioned solve or a sharp resonance.

For a matrix, its Euclidean operator norm is the largest output length produced
by a unit-length input vector: $\|H\|_2=\max_{\|z\|_2=1}\|Hz\|_2$.
Here `z` is a dimensionless complex vector, and this norm has the units of
the entries of `H`. The ordinary vector norm is the square root of the sum of
squared component magnitudes. These definitions give a useful remainder bound.

For a twice continuously differentiable response on the line segment from
zero to `η`, let $H_{jk}=\partial^2t/(\partial\eta_j\partial\eta_k)$ be the complex Hessian, whose units are
`(meV² nm)^-1`. Apply one-variable Taylor's theorem to $f(s)=t(E;u,s\eta)$ for
dimensionless `s∈[0,1]`:

$$
\mathcal R=\int_0^1(1-s)\,\eta^T H(E;u,s\eta)\eta\,ds,\qquad
|\mathcal R|\leq\frac12\sup_{0\leq s\leq1}\|H(E;u,s\eta)\|_2\,\|\eta\|_2^2.
$$

The Hessian matrix norm is its Euclidean operator norm; the product on the
right is dimensionless. No conjugate is inserted in the Taylor polynomial
because the coordinates `η` are real. The inequality follows from the norm
bound on a complex matrix bilinear form. It is local, with no universal radius
of accuracy. A bound uniform over an energy window needs a uniform Hessian
bound there. Gaussian coefficients have unbounded support, so “small variance”
alone is not a uniform guarantee for every draw.

<a id="eq-l2"></a>
## L2. Centered finite differences and their competing errors

For a real step `h>0` in `meV sqrt(nm)` and coordinate direction `e_k`, evaluate
two full solves with potentials `V_0 ± h φ_k`, holding the leads fixed:

$$
D_k^{(h)}=\frac{t(E;u,h e_k)-t(E;u,-h e_k)}{2h}
=D_k+\frac{h^2}{6}\partial_{\eta_k}^3 t(E;u,0)+O(h^4).
$$

The last expansion requires sufficient derivatives (for example five
continuous derivatives locally); the more basic second-order truncation
statement needs an appropriate third-derivative bound. The units of every
term are those of `D_k`. This differentiates real and imaginary parts together.
Differentiating `|t|`, `T`, or an unwrapped phase instead answers a different
question. An imaginary potential step would change the lossless physical
model. The usual real-valued complex-step shortcut is not being used.

If the two solves have absolute errors of scale `ε_num |t_±|`, subtraction
suggests a cancellation contribution of scale

$$
\frac{\varepsilon_{\rm num}(|t_+|+|t_-|)}{2h}.
$$

`ε_num` is a dimensionless error scale, not necessarily machine epsilon when
the solve is ill-conditioned; this expression is a diagnostic estimate, not
a rigorous forward-error bound. Large steps suffer Taylor truncation; tiny
steps magnify noise or fail to change a floating-point potential at all.
Measure convergence over several steps and compare with the independently
derived response below. Near a symmetry-enforced zero derivative, absolute
errors are more meaningful than relative errors divided by nearly zero.

<a id="eq-l3"></a>
## L3. Differentiate the boundary linear system

Use the dimensionless matrix `mathcal A` and solution `ψ` of S7 at a fixed
energy. Let $\gamma=\sqrt{v_R/v_L}>0$, so $t=\gamma e_{N-1}^T\psi$. For nodal potential
`V_j` in meV, take `τ` in meV as well. The leads and source do not change:

$$
\frac{\partial\mathcal A}{\partial V_j}=-\frac{e_je_j^T}{\tau},\qquad
\mathcal A\frac{\partial\psi}{\partial V_j}
=\frac{e_j\psi_j}{\tau}.
$$

These follow by differentiating $\mathcal A\psi=b$: move `(∂A)ψ` to the other side, which
changes its minus sign to a plus. Define `y` by the response solve
$\mathcal A^T y=e_{N-1}$. Then

$$
G_j(E)=\frac{\partial t}{\partial V_j}
=\frac{\gamma}{\tau}\,y_j\psi_j,\qquad
D_k(E)=\sum_j G_j(E)\Phi_{jk}.
$$

`ψ,y,γ` are dimensionless; `G_j` has units `meV^-1`, and `D_k` has the units
in L1. The transpose here is **ordinary transpose**, not Hermitian transpose:
we differentiate a complex linear functional, not a squared norm. An equivalent
Hermitian-adjoint implementation would have to conjugate its response vector
in the final contraction. qwave uses the former convention, and tests compare
it with full perturbed solves including unequal leads.

There is no extra spatial weight in `G @ Φ`: `G_j` is a derivative with
respect to the value at a discrete node. If defining a continuum-style
functional derivative $K(x_j)=G_j/w_j$, with `w_j` in nm, then
$\sum_jw_jK(x_j)\Phi_{jk}$ gives exactly the same result. `K` has units
`(meV nm)^-1`. Multiplying nodal `G_j` by `w_j` again would be wrong.

For a free discrete channel with common wave number $q=ka$, the outgoing
Green function gives the independent check

$$
G_j(E)=-\frac{i\,t_0(E)}{2\tau\sin q},\qquad\hbox{for every site }j.
$$

One derivation uses $(\mathcal A^{-1})_{nm}=\exp(iq|n-m|)/(2i\sin q)$, whose unit jump at
$n=m$ is verified by inserting it into the free tridiagonal row. Multiplying
its propagation from the source to `j` and from `j` to the output gives the
same total free phase for every `j`. This check detects a wrong response sign,
a missing factor, or taking a conjugate in the wrong place.

<a id="eq-l4"></a>
## L4. What the first-order approximation predicts about variance

With the retained zero-mean Gaussian coefficients of Chapter 5, define
$\delta t_{\rm lin}(E)=\sum_kD_k(E)\eta_k$. Its mean is zero, and

$$
\mathbb E_{\rm ens}[|\delta t_{\rm lin}(E)|^2]
=\sum_{j,k}D_j(E)D_k(E)^*\mathbb E_{\rm ens}[\eta_j\eta_k]
=\sum_k\lambda_k|D_k(E)|^2
=G(E)C_K G(E)^\dagger.
$$

This is a dimensionless squared amplitude. The second factor is conjugated;
`D_k²` would generally be complex and could not be a variance. `G` is a row
vector, and `C_K` is the nodal covariance in `meV²`. The last equality
substitutes $C_K=\Phi_K\Lambda_K\Phi_K^T$, with no extra quadrature weight because `G`
already differentiates nodal values. The equality only needs the covariance;
Gaussianity is not needed for this second-moment identity.

This is not automatically the variance of the **full nonlinear** amplitude.
Quadratic terms can bias its mean away from `t_0`, and change its variance.
Also `t_0+δt_lin` is a Taylor polynomial, not an exactly unitary scattering
matrix. Its squared magnitude can exceed one. Preserve and label such failures;
do not clip them to make first-order theory look physical.

## Validation that separates two approximations

Notebook 4 uses the actual `derivative_study`, `transmission_gradient`, and
`validate_linearization` functions. For the same fixed disorder draws it scales
`η` through small and moderate values, saves full-solve and Taylor complex
amplitudes, and plots their errors. A quadratic error trend at small scale is
evidence for a local expansion at those settings. It is not permission to use
it at all strengths or all energies.

To test KL truncation separately, compare a full covariance draw with its
retained-mode projection using full solves for **both**. To test Taylor error,
compare a retained-mode full solve with its linearization for the **same**
coefficients. Mixing these comparisons attributes omitted disorder to a
derivative failure, or hides a real nonlinear failure behind a mode count.
The library's paired validation keeps both quantities when full draws are
provided. Discretization and energy quadrature still require their own checks.
