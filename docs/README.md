# Phaseward documentation

Start with the [beginner-to-advanced learning route](derivations/README.md).
It introduces the mathematics before deriving the physical and numerical model,
then connects each equation to code, tests, and locally generated figures.

For installation and execution, use [HOW_TO_RUN.md](../HOW_TO_RUN.md).
The [scientific/software audit](audit_stage9.md) records actual checks, failures
fixed, measured outcomes and remaining limitations. See also
[contribution requirements](../CONTRIBUTING.md).

- [Learning chapters and four executable notebooks](derivations/README.md)
- [Compact glossary](derivations/glossary.md)
- [Theory → implementation → verification → figure](derivations/code-map.md)
- [Verified references and unresolved evidence](derivations/references.md)
- [Derivation-package validation and exact commands](validation_stage7.md)
- [Honest paper preparation, literature matrix and frozen-run export](paper/README.md)
- [Paper-export validation, exact commands and compiled review copies](validation_stage8.md)

For concise implementation details, use [architecture](architecture.md),
[scattering](scattering.md), [packet mathematics](mathematics.md),
[disorder](disorder.md), [sensitivity](sensitivity.md),
[optimization](optimization.md), and [experiments](experiments.md).
The optional [local GUI guide](gui.md) explains the interface and saved-result
viewer; the Python library and CLI work independently.

From the project root, after activating the installed environment:

```sh
python docs/derivations/run_notebooks.py --output results/learning-01
```

Use a new output name for every run. Each completed directory contains actual
executed notebooks, raw data, figures, and provenance; no account or Jupyter
installation is required for this runner.
