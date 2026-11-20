# Verified reading and reference limits

These primary teaching or software sources were opened and their relevant
contents checked on **2026-11-20**. Links are reading aids; no DOI, quotation,
publication-priority claim, or experimental support is inferred. The chapter
algebra is developed for qwave's declared conventions and checked against its
source and numerical tests.

| Source | Verified content and recommended use |
| --- | --- |
| [MIT OpenCourseWare, Quantum Physics I, Spring 2016 — lecture notes](https://ocw.mit.edu/courses/8-04-quantum-physics-i-spring-2016/pages/lecture-notes/) | The official index identifies notes on the Schrödinger equation (lecture 5), normalization and current (6), wave packets (7), stationary states (10), step-potential scattering (16), and scattering delay (18). Use these for further undergraduate study; match their reference-plane conventions before comparing amplitudes. |
| [MIT OpenCourseWare, Linear Algebra — symmetric matrices and positive definiteness](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/pages/positive-definite-matrices-and-applications/symmetric-matrices-and-positive-definiteness/) | Official undergraduate learning page on symmetry, eigenstructure, and positive definiteness. Background for the covariance diagonalization; not evidence for a specific disorder law. |
| [Teaching notes hosted at urbain.vaes.uk — week 3 PDF](https://urbain.vaes.uk/static/teaching/lectures/build/lectures-w3.pdf) | The PDF's printed pages 13–15 contain the KL theorem, projected coefficients, Gaussian-coefficient discussion, and mean-square truncation. The relevant theorem assumes a zero-mean square-integrable process on a bounded interval and continuous covariance. We verified that content; no unverified course date or publication metadata is assigned. |
| [College Board — AP Calculus BC course](https://apstudents.collegeboard.org/courses/ap-calculus-bc) | Official topics used for the learning-route boundary between single-variable calculus and the additional PDE, linear algebra, probability, and optimization material. |
| [SciPy — solve_banded](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html) | Official banded-system storage and solve interface. qwave's outgoing-lead boundary equations are derived in this course rather than attributed to this API page. |
| [SciPy — eigh](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.eigh.html) | Official Hermitian/real-symmetric eigenproblem and eigenvector-normalization contracts. Supports the choice to diagonalize the explicitly symmetric weighted covariance. |
| [SciPy — SLSQP](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html) | Official constrained minimizer, numerical stopping conditions, and finite-difference controls. Stopping success does not certify a global optimum or physical improvement. |

These pages can change; installed package versions are recorded in each run's
manifest, independently of the current documentation website version. Reference
availability is not required to run the notebooks offline after installation.

## Explicitly unresolved evidence

- A material-specific effective mass, gate-voltage calibration, and measured
  disorder covariance for a real semiconductor have **not** been supplied or
  independently validated. Such claims require manual reference checking and
  appropriate experimental evidence before being made.
- No verified publication establishing novelty, priority, or superiority of this
  project's sensitivity objective is claimed. A literature/prior-art review
  remains separate work. There are no placeholder authors or invented papers.
- The sources above do not establish a real-world failure probability. Numerical
  and mathematical checks in this package are conditional on the model.

