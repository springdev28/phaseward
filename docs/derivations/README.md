# Learning Phaseward: from calculus to transport sensitivity

This is a derivation course for the **existing `qwave` model**, not a claim that
the model describes every semiconductor or that its candidate optimizer wins.
Start with functions, derivatives, integrals, complex arithmetic, and elementary
probability. Each chapter introduces its additional tools before applying them.
The final chapters use undergraduate linear algebra, probability, perturbation
theory, and constrained optimization.

Phaseward models one coherent electron, a real static potential energy, one
spatial dimension, and a constant configurable effective mass. It does not model
decoherence, many electrons, contacts, fabrication, or a calibrated conversion
from electrode voltages to potential energy. The Schrödinger equation is a
physical assumption here. Numerical agreement within that assumption is not
experimental validation.

## A route through the material

| Read in order | Learn to do | Then verify |
| --- | --- | --- |
| [1. Mathematical tools](01-tools.md) | Track units; conjugate an inner product; interpret a matrix, eigenvector, and approximation | Work the short checks at the chapter's end |
| [2. The assumed model and current](02-model.md) | Derive conservation from the Schrödinger equation, and separate time from space | Notebook 1: free channel and conserved flux |
| [3. Stationary scattering and numerics](03-scattering.md) | Normalize open channels; derive discrete lead boundaries; compare with a continuum barrier | Notebook 1: complex-amplitude grid convergence |
| [4. Packets, probability, and fidelity](04-packets.md) | Change from wave number to energy; distinguish throughput from conditional overlap; interpret delay | Notebook 2: synthetic transformations and a physical device |
| [5. Correlated disorder](05-disorder.md) | Derive weighted covariance modes with correct units and variance | Notebook 3: empirical covariance and truncation |
| [6. Complex transmission sensitivity](06-sensitivity.md) | Differentiate a complex amplitude with respect to real potential coefficients; test a Taylor expansion | Notebook 4: finite differences and full solves |
| [7. The objective and its limits](07-objective.md) | Derive the surrogate; identify what it does and does not bound | Notebook 4: covariance contraction and a counterexample |

Keep the [glossary](glossary.md) and [equation → code → test → figure map](code-map.md)
open. [Verified references](references.md) offer further study; the derivations
here use the project's actual conventions, which can differ from a textbook's
choice of phase planes. The older [model reference](../mathematics.md),
[scattering notes](../scattering.md), [disorder notes](../disorder.md),
[sensitivity notes](../sensitivity.md), and [optimization notes](../optimization.md)
are compact implementation references after this course.

Suggested passes: read Chapters 1–4 for the physical quantities; revisit their
derivations with Notebook 1–2; then work Chapters 5–7 with Notebook 3–4. Advance
when you can explain each normalization without relying on the code. This is a
learning sequence, not a promised number of hours.

## Run all verification notebooks locally

From the Phaseward project folder, with its environment installed:

```sh
source .venv/bin/activate
python docs/derivations/run_notebooks.py --output results/learning-01
```

For a new installation, use Python 3.11 or later:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python docs/derivations/run_notebooks.py --output results/learning-01
pytest
```

The runner first checks that imported `qwave` source matches this workspace.
If an existing installation is stale, reinstall it; see
[the installation troubleshooting note](../validation_stage1.md). No Jupyter,
cloud service, API key, or GUI is required. The small runner uses standard Python
to execute this package's ordinary Python notebook cells, with fresh globals for
each notebook. It supports neither IPython magics nor arbitrary notebooks. It
does **not** sandbox Python: execute trusted project notebooks only.

You may instead open the `.ipynb` files in a local notebook editor using this
environment's Python kernel. The first cell sets up the repository import path
and a fresh output directory; changing its explicit `CONFIG` makes a new
educational run. Installing a notebook editor is optional, separate from qwave.

The notebooks call the real solver, packet, covariance, derivative, and objective
functions. Short assertions compare them with analytical identities, independent
library reference functions, or alternative contractions; they do not implement
another hidden transport pipeline. All seeds are **educational verification
seeds**, not training, development, or held-out experimental draws.

Each completed run contains executed notebooks with actual outputs, JSON
configurations and checks, CSV tables, NPZ raw arrays, PNG/SVG/PDF figures with
descriptions, and manifests with UTC time, source hashes, versions, hardware,
units, seeds, approximation settings, and file hashes. Existing directories are
rejected; use a fresh name. A failed run preserves partial data and a failure
record, and has no successful top-level manifest. See the generated `report.md`
and [this revision's validation record](../validation_stage7.md).

## Reading equations

An equation label such as **P4** is a stable link in the code map. Definitions and
units in a section apply to its subsequent equations until explicitly changed.
Each section states its domain and assumptions; a displayed equation does not
silently change the physical model. Public numerical values use nm, meV, and ps.
The differential equations can equivalently use SI, provided every factor uses
the same unit system. Probability is dimensionless; a density has inverse units
of its integration variable. Numerical tolerances are verification settings,
not physical constants.

## Where AP Calculus BC ends

The [official College Board course description](https://apstudents.collegeboard.org/courses/ap-calculus-bc)
includes one-variable differentiation/integration, parametric and polar curves,
elementary differential equations, and sequences and Taylor series. The table
below describes the additional tools this course needs, rather than claiming
that every school's coverage is identical.

| Familiar foundation | Additional study used here | First use |
| --- | --- | --- |
| Product rule and integration | Partial derivatives, PDE initial/boundary conditions, conservation laws | Chapter 2 |
| Complex-number arithmetic (a prerequisite here) | Complex-valued functions, conjugate inner products, Fourier transforms and distributions | Chapters 1, 4 |
| Taylor series of one real variable | Multivariable real Taylor expansions of complex responses; uniform error control | Chapter 6 |
| Vectors and sums | Eigenvectors, positive semidefinite matrices, weighted quadrature, conditioning and banded linear systems | Chapters 1, 3, 5 |
| Elementary probability | Random fields, covariance operators, Gaussian vectors, expectation of quadratic forms | Chapters 5–7 |
| One-variable extrema | Constrained multivariable optimization, feasible sets, local optima and computational budgets | Chapter 7 |

Full complex analysis studies holomorphic functions and contour integration.
It is valuable further study, but differentiating `t` with respect to a **real**
gate or disorder coefficient does not require holomorphic dependence on an
imaginary potential. Functional analysis supplies the deeper spectral and
Fourier theorems used here; their assumptions are stated, not proved from scratch.

## Self-check milestones

1. Explain why a right-going wave has positive current with the chosen time sign.
2. Explain why a stationary scattering wave is not a normalized single packet.
3. Recover the factor `sqrt(v_right/v_left)` and the energy Jacobian independently.
4. Give an example with high conditional fidelity and tiny transmitted probability.
5. Locate the **single** eigenvalue factor in the sensitivity objective.
6. Say which errors are discretization, KL truncation, Taylor remainder, sampling,
   or physical-model error. More samples cannot remove the other errors.

