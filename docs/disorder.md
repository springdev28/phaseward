# Bounded gates and correlated potential disorder

PROMPT 3 extends the existing coherent, elastic, constant-effective-mass model.
The mass, ideal semi-infinite leads, finite-difference dispersion, complex
amplitude normalization, and phase reference planes are unchanged; see
[scattering.md](scattering.md). Gate amplitudes and disorder are **potential
energies in meV**, not electrode voltages. An electrostatic voltage-to-energy
map would require additional physical inputs and is not inferred here.

## Finite channel and adjustable gates

The declared channel \([x_a,x_b]\) lies strictly inside the finite scattering
domain, with endpoints on its uniform physical grid. The surrounding buffers
and ideal leads receive no gate or disorder contributions. A separately
configured background potential remains as supplied. The total nodal potential is

\[
V_i=V_{\mathrm{background},i}+\sum_{j=1}^M u_j g_j(x_i)+\delta V_i.
\]

The number of entries in `model.gates.profiles` is \(M\); the default is four.
Each entry declares a name, shape, amplitude `amplitude_mev`, and increasing
`bounds_mev=[lower,upper]`. Bounds are checked before solving, without clipping.
`total_abs_bound_mev` also limits the absolute summed gate potential at every
sampled node. This bound applies to the gates, not to the supplied background or
unbounded Gaussian disorder. Overlapping gates can sum to more than an individual
amplitude, so both checks are explicit.

For a positive taper length \(b\le(x_b-x_a)/2\), define the channel envelope

\[
w_b(x)=\begin{cases}
\tfrac12[1-\cos(\pi\min(d(x)/b,1))],&d(x)>0,\\
0,&d(x)\le0,
\end{cases}\qquad d(x)=\min(x-x_a,x_b-x).
\]

It is continuously differentiable at both boundaries and the taper/plateau
joins. Gates require a positive taper. For a raw shape \(f_j\), the convention is

\[
g_j(x_i)=\frac{w_b(x_i)f_j(x_i)}{\max_i|w_b(x_i)f_j(x_i)|}.
\]

Thus \(g_j\) is dimensionless with sampled peak absolute value one, and \(u_j\)
has units meV. This is **peak normalization**, not integral or L² normalization.
The denominator is stored. Grid refinement can change it slightly; compare the
resolved gate arrays when studying spatial convergence. An unresolved/zero gate
is rejected.

Supported raw shapes are:

| `kind` | Parameters | Raw shape |
| --- | --- | --- |
| `gaussian` | `center_nm`, `sigma_nm` | \(e^{-(x-c)^2/(2s^2)}\) |
| `raised_cosine` | `center_nm`, `half_width_nm` | \([1+\cos(\pi(x-c)/a)]/2\) for \(|x-c|<a\), zero otherwise |
| `tabulated` | `x_nm`, dimensionless `values`, `interpolation: "pchip"` | Shape-preserving C¹ cubic interpolation, followed by the same envelope and normalization |

A user-supplied table must cover the whole channel; no extrapolation or executable
expression is accepted. Signed table values are supported. A complete alternative
gate entry is, for example:

```json
{
  "name": "custom_gate",
  "amplitude_mev": 8,
  "bounds_mev": [-30, 30],
  "shape": {
    "kind": "tabulated",
    "x_nm": [-30, -10, 0, 10, 30],
    "values": [0, 0.2, 1, 0.4, 0],
    "interpolation": "pchip"
  }
}
```

The default four Gaussian gates have centers [-18,-6,6,18] nm, widths 4 nm,
amplitudes [8,15,12,6] meV, individual bounds [-30,30] meV, a 5 nm channel taper,
and a 60 meV bound on their sum. These are illustrative fixed settings, not an
optimized device or evidence for a robust-control method.

## Nodal covariance and boundary handling

On the actual channel nodes, the default zero-mean Gaussian random vector has
covariance

\[
C_{ij}=\mathbb E[\delta V_i\delta V_j]
=\sigma^2\exp[-(x_i-x_j)^2/(2\ell^2)].
\]

`sigma_mev` is the pointwise standard deviation before optional tapering;
`correlation_length_nm` is \(\ell\), in nm. Covariance has units meV².
Three explicit kernels are implemented, with \(r=|x-x'|\):

| Kernel | Correlation \(\kappa(r)\) | Value at \(r=\ell\) |
| --- | --- | --- |
| `gaussian` (squared exponential) | \(e^{-r^2/(2\ell^2)}\) | \(e^{-1/2}\) |
| `exponential` | \(e^{-r/\ell}\) | \(e^{-1}\) |
| `matern32` | \((1+\sqrt3 r/\ell)e^{-\sqrt3 r/\ell}\) | \((1+\sqrt3)e^{-\sqrt3}\) |

The same length parameter has the declared kernel-specific meaning; it is not
called a universal e-folding distance. These are standard covariance families;
see [Rasmussen and Williams, Gaussian Processes for Machine Learning, chapter 4](https://gaussianprocess.org/gpml/chapters/RW4.pdf).

`boundary_taper_nm=0` is the default: the covariance above applies exactly on
the channel nodes, including endpoints. Samples are set to zero outside that
channel, introducing an explicit hard edge inside the finite domain. It does
not wrap periodically or extend disorder into the ideal leads. Node sampling
of this edge remains a spatial discretization choice.

An optional positive disorder taper \(b_d\) instead uses
\(C_{ij}=\sigma^2w_{b_d}(x_i)\kappa(|x_i-x_j|)w_{b_d}(x_j)\). This preserves
positive semidefiniteness and changes local variance to \(\sigma^2w_{b_d}^2\).
The result is not spatially stationary near the boundaries. Gate taper and
disorder taper are independent settings; neither is silently applied to the other.
Samples are not clipped, smoothed after generation, spatially demeaned, or
renormalized to have an exact sample RMS, since those operations change covariance.

## Spatially weighted Karhunen–Loève convention

For the continuum covariance operator,

\[
\int_{x_a}^{x_b}C(x,x')\phi_k(x')dx'=\lambda_k\phi_k(x),\qquad
\int_{x_a}^{x_b}\phi_j(x)\phi_k(x)dx=\delta_{jk}.
\]

Let \(W=\operatorname{diag}(w_i)\) contain positive spatial trapezoidal weights
in nm, including half-weights at the channel endpoints. The nodal approximation
is \(CW\Phi=\Phi\Lambda\), not the unweighted eigenproblem of \(C\). Solve the
real symmetric problem

\[
B=W^{1/2}CW^{1/2}=Q\Lambda Q^T,\qquad Q^TQ=I,\qquad
\Phi=W^{-1/2}Q.
\]

Then \(\Phi^TW\Phi=I\) and the full nodal covariance reconstructs as
\(C=\Phi\Lambda\Phi^T\). The implementation uses
[SciPy's symmetric `eigh` solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.eigh.html)
with the divide-and-conquer driver, sorted in decreasing eigenvalue order.
Ignoring \(W\) would make operator eigenvalues scale incorrectly with node count;
tests explicitly refine the physical grid to detect that error.

The single convention used in arrays, derivatives, and reports is:

\[
\boxed{\delta V_K(x)=\sum_{k=1}^K\eta_k\phi_k(x),\qquad
\eta_k=\sqrt{\lambda_k}\,z_k,\quad z_k\overset{\mathrm{iid}}\sim N(0,1).}
\]

| Quantity | Units | Normalization or variance |
| --- | --- | --- |
| \(\phi_k\) | nm⁻¹ᐟ² | \(\Phi^TW\Phi=I\); no eigenvalue factor in shapes |
| \(\lambda_k\) | meV² nm | Covariance-operator eigenvalue |
| \(\eta_k\) | meV √nm | \(\mathbb E\eta_j\eta_k=\lambda_k\delta_{jk}\) |
| \(z_k\) | dimensionless | Independent unit-variance coefficients |
| \(\delta V\) | meV | Nodal potential-energy disorder |

In particular, \(\eta_k\) is **not** unit variance. Multiplying it by another
\(\sqrt{\lambda_k}\) when constructing disorder or sensitivity objectives would
count the covariance twice. `eta_mev_sqrt_nm` and `standard_normals` are stored
under distinct names. The Python sampler returns full samples and their
K-mode projections from the same coefficient draws.

The retained covariance and integrated variance fraction are

\[
C_K=\Phi_K\Lambda_K\Phi_K^T,\qquad
f_K=\frac{\sum_{k=1}^K\lambda_k}{\sum_iw_i C_{ii}}.
\]

For an untapered channel the denominator is \(\sigma^2(x_b-x_a)\). The expected
discarded squared spatial L² norm is \(\sum_{k>K}\lambda_k\). No rescaling is
used to restore discarded variance: pointwise variances and correlations change
under truncation, and a large integrated fraction alone does not bound the
transport error. `qwave sensitivity` measures that transport error separately.

Small negative eigenvalues within \(64N\epsilon\max_k|\lambda_k|\) are treated
as eigensolver roundoff, set to zero, and counted with their removed mass. Larger
negative values cause failure. No covariance jitter is added. Retained modes
must have eigenvalues above this same resolution threshold. The full sampler
also includes smaller positive eigenvalues, whose effects are archived. Raw
minimum eigenvalue, orthogonality error, and covariance reconstruction error are
reported. A zero covariance can be constructed through the API, but a KL run
requires positive sigma and resolved modes; sensitivity scale zero gives a clean
device without inventing zero-variance directions.

Mode signs are fixed by making the largest-magnitude weighted eigenvector entry
positive. Signs or bases inside degenerate eigenspaces may change with roundoff,
grid construction, or library version. Each run saves the actual grid, full
eigenbasis, eigenvalues, coefficients, and versions. Reproducibility is based on
those stored data, not a claim of identical eigenvectors across all machines.

## Sampling and empirical verification

`seed` constructs a local NumPy `Generator(PCG64(seed))`. Draws have shape
`(sample_count, channel_nodes)` and are retained, along with their scaled
coefficients and full/KL potentials. The examples use seed 1729 for covariance
validation and a different seed, 271828, for sensitivity validation. Neither is a
training or optimization set. Later training/validation/held-out partitions must
remain separate.

From \(n\) independent draws, the stored covariance uses the sample mean and
denominator \(n-1\). Its Gaussian sampling statistics satisfy

\[
\operatorname{Var}(\widehat C_{ij})=
\frac{C_{ij}^2+C_{ii}C_{jj}}{n-1},\qquad
\operatorname{Var}(\bar V_i)=\frac{C_{ii}}n,
\]

\[
\mathbb E\|\widehat C-C\|_F^2=
\frac{\|C\|_F^2+(\operatorname{tr}C)^2}{n-1}.
\]

Reports compare full samples with \(C\), and truncated samples with \(C_K\),
using variance ratios, covariance error, mean/variance errors in standard-error
units, and lag-averaged pair correlations. Zero-variance nodes are excluded from
normalized correlations. At long lags fewer spatial pairs contribute; pair
estimates are correlated and are not treated as independent draws.

The runtime guard checks maximum mean and variance errors below six individual
Gaussian standard errors and covariance Frobenius error below four expected RMS
units. This is a documented numerical regression screen, not a simultaneous
confidence interval or a physical law. Results and flags are saved even if the
screen fails. Statistical agreement must be interpreted with sample count.
Tests also verify a specific off-diagonal covariance entry and the omitted-mode
L² norm against their independent Gaussian sampling uncertainties.

## Reproducible command and outputs

```sh
qwave config-check examples/disorder.json
qwave disorder --config examples/disorder.json --output results/my-disorder
```

The output directory must be new. The complete example uses a 60 nm channel
inside [-40,40] nm, 0.2 nm spacing, sigma=2 meV, ell=5 nm, K=8, and 4096 draws.
Dense covariance matrices are limited to 801 channel nodes and sample matrices
to four million values, to keep these local CPU runs modest.

The bundle includes exact settings, metrics, a manifest written last, complete
NPZ arrays, gate/mode/eigenvalue CSVs, variance and correlation CSVs, and the first
five paired sample profiles in CSV. All samples remain in NPZ. Figures show
gate contributions and sum, eigenvalue decay and retained variance, mode shapes,
representative disorder, and empirical covariance checks, in PNG/SVG/PDF.
Use `numpy.load(..., allow_pickle=False)`; NPZ embeds JSON provenance as a Unicode
scalar. [Stage-3 validation](validation_stage3.md) records the executed outcomes.
