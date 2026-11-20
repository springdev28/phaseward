# Research-error checklist

Record evidence paths and reviewer initials for every checked item. A checked
box without evidence is not validation. Unresolved items stay visible.

- [ ] **Data leakage:** disjoint exact seed partitions, across prior runs too;
  all designs frozen before final draws; no held-out tuning or restarts.
- [ ] **Baseline fairness:** same gate count/shapes/bounds, target, feasibility
  constraints, starts and search work cap; no extra candidate-only tuning.
  Include preflight, postflight, setup and evaluation costs separately.
- [ ] **Cherry-picked plots:** all prespecified cases/methods and failed searches
  retained; full trial distributions; index includes every source figure.
  State why this run was chosen and disclose prior exploration.
- [ ] **Convergence:** spatial grid, energy quadrature/window, KL truncation,
  derivative step, independent scattering method and sample count checked
  separately. Fixed-device convergence does not certify optimized devices.
- [ ] **Phase/gauge consistency:** t and r remain complex; unit-flux normalization,
  lead reference planes and Fourier sign fixed; global phase invariance tested;
  delay bounds and boundary hits disclosed; no unrestricted alignment.
- [ ] **Negligible-throughput fidelity:** P and raw/aligned F shown separately;
  low-P flags and undefined normalized states retained; loss conventions declared.
- [ ] **Simulation versus hardware:** no fabricated experiments, voltage mapping,
  material universality, devices, contacts or fabrication validation. State model
  omissions and distinguish numerical error from physical approximation.
- [ ] **Covariance calculus:** weighted orthonormality, units and variance scaling
  preserved; lambda included exactly once; gate normalization distinguished.
- [ ] **Surrogate limitations:** J is neither fidelity nor failure probability;
  higher-order and omitted-mode errors measured before robustness claims.
- [ ] **Statistics:** pairing, inference unit, missingness, relative denominator,
  multiplicity and practical threshold declared. Confidence intervals conditional
  on frozen designs are not campaign-wide uncertainty estimates.
- [ ] **Provenance:** matching run/config/source/seed hashes; all copied tables and
  figures audited; manifests unsigned unless a real external attestation exists.
  Complete source release and environment available before claiming reproducibility.
- [ ] **Literature:** every citation identity checked on a primary record; full-text
  scope and numerical claims reviewed before final use; unverified gaps flagged;
  no novelty inference from missing search results or a small matrix.
- [ ] **Manuscript:** no fabricated Results, abstract performance claim, conclusion,
  author list, data repository DOI or publication status. Unfavorable results stay.
