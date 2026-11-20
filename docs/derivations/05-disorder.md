# 5. Gates and correlated random potential energy

Prerequisites: weighted integrals and symmetric matrices from Chapter 1. This
chapter introduces random vectors, covariance, and covariance eigenfunctions
before using a Karhunen–Loève (KL) representation. Disorder is a static real
potential sampled for an ensemble of separate coherent-scattering calculations.
It is not time-dependent noise during one solve.

<a id="eq-g1"></a>
## G1. Deterministic gates and random disorder are different bases

On a finite physical channel $D=[x_a,x_b]$ in nm, write the potential in meV as

$$
V(x;u,\eta)=V_{\rm background}(x)
+\sum_{j=1}^{M}u_jg_j(x)+\delta V(x;\eta).
$$

`u_j` are real gate-induced **energy** amplitudes (meV), `M` is a finite gate
count, and `g_j` are dimensionless real profiles. The library normalizes each
sampled gate profile to peak absolute value one, applies declared individual
coefficient bounds and a summed-potential bound, and can taper profiles to
zero before the ideal leads. Sampled Gaussian, raised-cosine, or supplied
profiles are numerical choices that must be saved. They are not the spatial
integral-normalized covariance functions introduced below. No electrode
voltage calibration is implied by `u_j`.

<a id="eq-d1"></a>
## D1. Covariance measures joint fluctuations

A random field assigns a random real value `δV(x)` to each point. Assume zero
mean and finite second moments. Expectation `E_ens` means an ensemble average,
not electron energy `E`. Define the covariance kernel by

$$
C(x,x')=\mathbb E_{\rm ens}[\delta V(x)\delta V(x')],\qquad
C(x,x')=\sigma^2\exp\!\left[-\frac{(x-x')^2}{2\ell^2}\right]
\quad\hbox{for the Gaussian default}.
$$

Here `x,x',ell` are in nm, $\sigma\geq0$ is in meV, and `C` has units `meV²`.
The diagonal gives point variance; its square root is pointwise standard
deviation. Without tapering, the correlation at separation `ell` is
$\exp(-1/2)$, not $\exp(-1)$. The latter separation is $\sqrt{2}\ell$ for this
kernel. Other kernels have different definitions of their scale parameter.

“Gaussian kernel” names a covariance shape. “Gaussian random field” additionally
means every finite vector of sampled values is jointly Gaussian. A covariance
alone does not specify a non-Gaussian field's higher moments. The generator
here chooses the Gaussian distribution explicitly.

For a real dimensionless vector `c` and covariance matrix $C_{ij}=C(x_i,x_j)$,

$$
c^T Cc=\mathbb E_{\rm ens}\left[\left(\sum_i c_i\delta V(x_i)\right)^2\right]\geq0.
$$

Both sides have units `meV²`. This proves every valid covariance is symmetric
positive semidefinite. Conversely the Gaussian Fourier identity in P7 gives
the kernel representation

$$
C(x,x')=\frac{\sigma^2\ell}{\sqrt{2\pi}}
\int_{\mathbb R}e^{-\ell^2 k^2/2}e^{ik(x-x')}\,dk.
$$

Here `k` is a Fourier variable in inverse nm over the whole real line, not the
positive lead wave number of the transport problem. The result has units
`meV²`. Inserting this expression in the quadratic form makes the integrand
proportional to $|\sum_i c_i e^{ikx_i}|^2$, proving nonnegativity. This is a
covariance identity, not a statement about negative-momentum electrons.
Boundary tapering by a declared dimensionless
real envelope `b(x)` changes the kernel to $b(x)C(x,x')b(x')$. This remains
positive semidefinite but changes the diagonal variance near the edges. It is
not stationary there. The potential outside the physical channel is zero
disorder; the uniform lead potentials remain fixed.

<a id="eq-d2"></a>
## D2. Eigenfunctions of a covariance operator

First generalize a matrix-vector product: an **integral operator** replaces
the column sum by integration over a finite domain. For a real continuous
symmetric positive covariance kernel on `D`, consider

$$
\int_D C(x,x')\phi_k(x')\,dx'=\lambda_k\phi_k(x),\qquad
\int_D\phi_j(x)\phi_k(x)\,dx=\delta_{jk}.
$$

`delta_jk` is the Kronecker symbol (one for equal indices, zero otherwise), not
the Dirac distribution. Real shapes `φ_k` have units `nm^(-1/2)`; nonnegative
eigenvalues `λ_k` have units `meV² nm`. This follows immediately by balancing
the first equation's units. Sort the eigenvalues in decreasing order.

The spectral theorem for this compact positive integral operator, with finite
trace (sum of eigenvalues) here, supplies orthonormal modes on the covariance's supported subspace.
This extends the finite symmetric-matrix theorem; proving that extension
requires functional analysis. The expansion and mean-square convergence below
use those assumptions, not an assertion about an arbitrary discontinuous
infinite-domain kernel.

Project a zero-mean field onto a mode:

$$
\eta_k=\int_D\phi_k(x)\delta V(x)\,dx,\qquad
\mathbb E_{\rm ens}[\eta_j\eta_k]
=\int_D\!\int_D\phi_j(x)C(x,x')\phi_k(x')\,dx'\,dx
=\lambda_k\delta_{jk}.
$$

Coefficients `η_k` have units `meV sqrt(nm)` and variance `λ_k`. The middle
equality interchanges expectation and integration under the finite-second-moment
assumptions. The last equality applies the eigen-equation and orthonormality.
For a Gaussian field, these uncorrelated Gaussian coefficients are independent.
Uncorrelated coefficients need not be independent for a non-Gaussian field.

<a id="eq-d3"></a>
## D3. Exactly one variance factor in a truncated KL sample

Let `K` be a declared finite number of resolved positive modes, and let
`z_k` be independent real standard normal random numbers with mean zero and
variance one. qwave's convention is

$$
\eta_k=\sqrt{\lambda_k}\,z_k,\qquad
\delta V_K(x)=\sum_{k=1}^K\eta_k\phi_k(x),\qquad
C_K(x,x')=\sum_{k=1}^K\lambda_k\phi_k(x)\phi_k(x').
$$

`z_k` is dimensionless; `η_k` contains the variance. The shapes do **not**
contain $\sqrt{\lambda_k}$. Including that factor again in the sampled potential or
in derivatives with respect to `η` double counts the covariance. One can
instead differentiate with respect to `z`, but then the chain rule changes
the derivative and the objective; Chapter 7 makes that equivalence explicit.

Mean-square truncation error and retained integrated variance obey

$$
\mathbb E_{\rm ens}\!\left[\int_D|\delta V-\delta V_K|^2\,dx\right]
=\sum_{k>K}\lambda_k,\qquad
f_K=\frac{\sum_{k=1}^K\lambda_k}{\sum_{k\geq1}\lambda_k},\qquad
\sum_{k\geq1}\lambda_k=\int_D C(x,x)\,dx.
$$

The error and sums have units `meV² nm`; `f_K` is dimensionless and the
denominator must be positive. Orthogonality removes cross terms in the norm;
expectation supplies each coefficient variance. Retaining a large fraction of
potential variance does not guarantee the same fraction of transport accuracy:
an omitted mode might couple strongly to a sensitive response. No sample is
rescaled afterward to force its variance to equal the nominal value.

<a id="eq-d4"></a>
## D4. Derive the weighted numerical eigenproblem

Let channel nodes be `x_i`, with positive trapezoidal weights `w_i` in nm. Set
$W_x=\operatorname{diag}(w_i)$ and $C_{ij}=C(x_i,x_j)$ in `meV²`. The quadrature eigenproblem is
$CW_x\phi=\lambda\phi$. This matrix is not generally symmetric in the ordinary dot
product. Change coordinates with $q=W_x^{1/2}\phi$ to obtain a symmetric problem:

$$
S=W_x^{1/2} C W_x^{1/2}=Q\Lambda Q^T,\qquad
Q^TQ=I,\qquad \Phi=W_x^{-1/2}Q.
$$

`S` and `Λ` have units `meV² nm`, `Q` is dimensionless, and each column of `Φ`
has units `nm^(-1/2)`. For a finite matrix, its trace `tr` is the sum of its
diagonal entries. Multiplication verifies

$$
\Phi^T W_x\Phi=I,\qquad C=\Phi\Lambda\Phi^T,\qquad
\operatorname{tr}(W_x C)=\sum_k\lambda_k.
$$

These identities are exact for a full positive semidefinite sampled matrix in
exact arithmetic. They use **spatial** weights, not energy weights. Merely
diagonalizing `C` and calling its eigenvectors spatially normalized would
make eigenvalues and coefficients grid-dependent in the wrong units.

The library diagonalizes `S` with a real symmetric eigensolver. Tiny negative
eigenvalues at its declared roundoff threshold are clipped to zero and their
mass is reported; materially indefinite covariance is rejected. With clipping,
the reconstructed covariance differs from the supplied matrix by that reported
roundoff correction. Unresolved retained modes are rejected. Eigenvector signs
are chosen deterministically for display; sign flips do not change covariance.
Within an exactly degenerate subspace, even shapes are not unique.

The numerical coefficient vector for a sampled field is $\eta=\Phi^T W_x\delta V$.
Sampling with $\delta V=\Phi_K\sqrt{\Lambda_K}z$ therefore has exactly the truncated covariance
`C_K` in the mathematical Gaussian generator. Finite sample covariance still
fluctuates. Notebook 3 compares its empirical covariance with `C_K`, separately
from comparing `C_K` with `C`. It saves the draws, weights, shapes, eigenvalues,
seed, clipping diagnostics, and retained fraction.

## Numerical verification and interpretation

For a real matrix `M`, its Frobenius norm is the square root of the sum of all
squared entries. This treats the array as one long vector; its units are those
of an entry. For `N_s>1` independent Gaussian field draws, form the usual
sample covariance `C_hat` by subtracting the sample mean and dividing the sum
of outer products by `N_s-1`. It is unbiased for the generated covariance
`C_gen` (full or retained, as explicitly selected). The Gaussian fourth-moment
identity gives each entry's variance, and summing those variances gives

$$
\operatorname{Var}(\widehat C_{ij})=
\frac{(C_{{\rm gen},ij})^2+C_{{\rm gen},ii}C_{{\rm gen},jj}}{N_s-1},\qquad
\mathbb E\|\widehat C-C_{\rm gen}\|_F^2=
\frac{\|C_{\rm gen}\|_F^2+(\operatorname{tr}C_{\rm gen})^2}{N_s-1}.
$$

These quantities have units `meV⁴`; their square roots supply an RMS error
scale in `meV²`. This uses Gaussian independent **draws**; nodes within a draw
are correlated. The formula for Gaussian fourth moments is an additional
probability result, not a consequence of calculus alone: its zero-mean form
is $\mathbb E[X_iX_jX_kX_l]=C_{ij}C_{kl}+C_{ik}C_{jl}+C_{il}C_{jk}$.
Here the `X` are jointly Gaussian values in meV and `C` is their covariance.
It follows, for example, by differentiating their moment-generating function
$\mathbb E[e^{s^TX}]=\exp(s^TCs/2)$ four times at zero; `s` has units
`meV^-1`. Centering by the sample mean yields the `N_s-1` divisor above.
This scale is not a simultaneous confidence interval for all entries. The
notebook uses a declared broad multiple as a regression check and keeps the
measured error, rather than asserting that empirical covariance is exact.

Increasing the number of samples tests empirical covariance uncertainty.
Increasing `K` tests representation error; refining `x` tests the covariance
quadrature and ultimately the transport solver. Do not mix these checks. A
single seed that appears visually smooth proves neither the correlation length
nor the covariance scaling. Notebook 3 checks coefficients and sampled fields,
while the existing disorder tests also check amplitude scaling, tapering, and
grid convergence. None of these establish a real semiconductor's disorder law.
