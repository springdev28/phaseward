# Compact glossary and unit reference

Definitions use the conventions derived in this course. A unit of **1** means
dimensionless. The same letter can mean different things only where explicitly
qualified: `t(E)` is transmission amplitude; `t_obs` is observation time.

| Symbol or term | Meaning | Public units / caution |
| --- | --- | --- |
| `x`, `a`, `L`, `ell` | Position, grid spacing, plane separation, covariance length scale | nm |
| `E`, `V`, `u_j`, `τ` | Electron energy, potential energy, gate energy amplitude, discrete hopping energy | meV; not electrode voltage |
| `m*`, `m_e` | Effective mass, free-electron mass | kg internally; configurable ratio `m*/m_e` is dimensionless |
| `ħ` | Planck's constant divided by `2π` | J s internally, meV ps in reconstruction |
| `k`, `q=ka` | Positive wave number, dimensionless lattice wave number | nm⁻¹, 1 |
| `v` | Positive lead group speed | solver returns m/s; reconstruction converts to nm/ps |
| `Ψ` | Normalizable position wavefunction | nm⁻¹ᐟ²; its squared magnitude is a density, not a path |
| `ρ_x`, `j` | Position probability density, signed probability current | nm⁻¹, ps⁻¹ in a consistent nm/ps convention |
| `χ_E` | Stationary flux-basis spatial function | (ps/nm)¹ᐟ²; not a unit-norm packet |
| `t`, `r` | Complex flux transmission/reflection coefficients | 1; phase planes must be specified |
| `T`, `R` | Energy-resolved transmission/reflection probabilities | 1; squared magnitudes of flux coefficients |
| `A(E)`, `B(E)` | Incoming and unnormalized transmitted energy amplitudes | meV⁻¹ᐟ²; `B=A t` |
| `a_k(k)` | Wave-number amplitude | nm¹ᐟ²; differs from `A` by a Jacobian |
| `ρ_E`, `w(E)` | Energy probability density, normalized objective importance | meV⁻¹; default `w=ρ_E` |
| `σ_E`, `Z_W` | Untruncated Gaussian density bandwidth, mass in the chosen energy window | meV, 1 |
| `P_trans` | Integrated transmitted probability (throughput) | 1; reported independently of fidelity |
| `g`, `h` | Normalized transmitted and target spectral states | meV⁻¹ᐟ²; undefined if their norm vanishes |
| `F_raw`, `F_aligned` | Squared normalized overlap, with/without a declared bounded lag search | 1; conditional on transmission |
| `δ`, `s` | Specified lag, searched alignment lag | ps; positive lag means the output is later |
| `g_j(x)` | Deterministic gate profile | 1; sampled peak absolute value one |
| `δV`, `σ` | Random potential, nominal pointwise standard deviation before taper | meV |
| `C(x,x')`, `C_K` | Full covariance kernel/matrix, retained-mode covariance | meV² |
| `W_x`, `w_j` | Diagonal spatial quadrature matrix, its positive weights | nm; distinct from energy weights |
| `φ_k`, `Φ` | Spatially normalized covariance mode, sampled mode matrix | nm⁻¹ᐟ² |
| `λ_k` | Variance of a KL coefficient; covariance-operator eigenvalue | meV² nm |
| `η_k`, `z_k` | Physical KL coefficient, unit-variance normal coordinate | meV √nm, 1; variance belongs in `η` |
| `G_j`, `D_k` | Complex derivative of transmission with respect to a nodal potential or a KL coefficient | meV⁻¹, (meV √nm)⁻¹ |
| `J`, `J/σ²` | Expected weighted first-order squared complex change, optional amplitude-normalized quantity | 1, meV⁻²; neither is fidelity |
| `*`, `T`, `†` on an expression | Complex conjugate, ordinary transpose, conjugate transpose | `T(E)` is instead a probability |
| Inner product | Conjugate-weighted integral or sum comparing amplitudes | First slot conjugated |
| Jacobian | Derivative needed when changing the integration variable | Here `dE/dk=ħv` |
| Self-energy | Boundary term after eliminating a semi-infinite lead | Energy; not a sampled random field |
| Retarded/outgoing | Boundary condition consistent with waves leaving the finite region | Depends on the declared time sign |
| Evanescent | Exponential spatial behavior where propagation is forbidden locally | Does not define an open flux channel |
| PSD | Positive semidefinite: every quadratic form is nonnegative | Required of a covariance |
| KL truncation | Keeping a specified set of covariance modes | Different from Taylor truncation |
| Surrogate | A computable objective used in place of the desired outcome | Its usefulness requires independent evaluation |
| Residual / conditioning | Equation mismatch / sensitivity of a solution to perturbations | Small residual alone does not prove small forward error |
| Held out | Data reserved until designs and evaluation rules are frozen | Not a source of optimizer tuning |

