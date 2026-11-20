# Derivation-package validation

Validation recorded on 2026-11-20. This is a documentation and educational
verification stage. The production `src/qwave` implementation, package version
and dependencies were not changed. No optimizer was retuned or held-out
experimental distribution altered. The new numerical examples are explicitly
educational; they are not evidence of laboratory transport or method superiority.

## Deliverables and architecture

The [learning route](derivations/README.md) contains seven sequenced chapters,
a compact glossary, verified primary references, and an equation-to-code map.
It starts with calculus, units and complex arithmetic, then introduces PDEs,
current, Fourier normalization, covariance operators, complex perturbation
derivatives, and a constrained surrogate objective. AP Calculus BC boundaries
and the additional undergraduate tools are marked explicitly.

```text
docs/
├── README.md
├── validation_stage7.md
└── derivations/
    ├── README.md
    ├── 01-tools.md
    ├── 02-model.md
    ├── 03-scattering.md
    ├── 04-packets.md
    ├── 05-disorder.md
    ├── 06-sensitivity.md
    ├── 07-objective.md
    ├── glossary.md
    ├── references.md
    ├── code-map.md
    ├── code-map.json
    ├── verification.py
    ├── run_notebooks.py
    ├── check_package.py
    └── notebooks/
        ├── 01_scattering.ipynb
        ├── 02_packets.ipynb
        ├── 03_covariance.ipynb
        └── 04_sensitivity_objective.ipynb
```

The notebooks call the installed, source-verified qwave library. The helper
records provenance and artifacts; it implements no second physics solver.
The standard-library runner executes ordinary Python cells and embeds their
actual text/PNG outputs in executed copies. It needs no Jupyter, IPython,
Streamlit, account or network connection. A local notebook editor remains optional.

## Executions and actual outcomes

The final [executed package](../results/stage7-learning-verified/report.md) completed in
**23.38 seconds** on this native Apple Silicon arm64 process.
First-run font-cache work is included. Times are observations on this run, not
a performance guarantee. Each notebook has a configuration, JSON checks, CSV
tables, raw NPZ arrays with units, a manifest, and PNG/SVG/PDF figures.

| Notebook | Numerical checks | Figures | Time (s) |
| --- | ---: | ---: | ---: |
| [01_scattering.ipynb](../results/stage7-learning-verified/01_scattering.executed.ipynb) | 5 passed | 2 | 17.31 |
| [02_packets.ipynb](../results/stage7-learning-verified/02_packets.executed.ipynb) | 6 passed | 2 | 1.20 |
| [03_covariance.ipynb](../results/stage7-learning-verified/03_covariance.executed.ipynb) | 4 passed | 2 | 1.87 |
| [04_sensitivity_objective.ipynb](../results/stage7-learning-verified/04_sensitivity_objective.executed.ipynb) | 7 passed | 2 | 2.86 |

The final run has **22 passing notebook checks** and eight figures in three
formats. These checks distinguish throughput from conditional fidelity, retain
complex phase, use the proper energy measure and discrete velocity, and verify
the weighted KL covariance convention and its sensitivity contraction.

Selected measured values (exact configurations and full arrays are linked below):

| Check | Actual result | Interpretation |
| --- | --- | --- |
| Continuum barrier at dx=0.0625 nm | max complex t error 0.00089654366; max T error 2.5740601e-05 | Continuum discretization error remains despite near-exact discrete conservation |
| Complex barrier refinement | error ratios 4.003554, 4.000894 | Approximately second order for these fixed energies and grid sequence |
| Barrier conservation | largest error 7.8604e-14 | A discrete lossless consistency check, not a continuum accuracy bound |
| Physical Gaussian-barrier packet | P=0.946850154, raw F=0.994699372, aligned F=0.999631192, lag=0.009299133 ps | Free target, same planes, lag bounded to [-0.15,0.15] ps |
| Lead reconstruction | density L1 change on energy refinement 4.3161e-11 | Fixed right-lead window, no display renormalization |
| Six-mode covariance | retained variance fraction 0.862377629; empirical covariance relative Frobenius error 0.03667795 | 4096 Gaussian draws, seed 730001; sampling error compared with retained covariance |
| Actual fixed-device sensitivity | J=0.0360547874; J/sigma²=0.0090136969 meV^-2 | Nodal covariance contraction agrees with the actual modal objective |
| Synthetic global-phase family | surrogate=0.0047399364; raw F=1.0 | Positive surrogate does not imply conditional fidelity loss |
| Strength multiplier 4 | Taylor RMS error 0.76939746; 501 linearized energy/draw values exceed one | The Taylor approximation is not reliable in this regime; values were retained, not clipped |

The last row is an unfavorable approximation outcome, not a failed physical
solver or a result to hide. Full-solve conservation checks passed. Small-scale
Taylor error ratios were near four; KL truncation errors were saved separately.
The derivative study reached a numerical noise floor and flagged all four
modes as unresolved at the 1e-30 coefficient step. A zero difference there
was not accepted as zero sensitivity.

Regression tolerances were declared in the notebooks before their first run.
Barrier tolerances use the existing spatial convergence study; Gaussian
identities use wide-window tail checks, quadrature refinement and roundoff
scales. Empirical covariance uses an expected Gaussian sampling RMS, not a
simultaneous confidence interval. Broad numerical guards are not physical
constants or rigorous global error estimates. Raw values slightly above one
at roughly floating-point roundoff remain visible in saved metrics.

## Automated tests, traceability, and rendering

Full project test output:

```text
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
232 passed in 93.36s (0:01:33)
```

The six new tests execute all notebooks and audit their artifacts; check the
exact normalized-state projection identity, the leading projected Taylor
coefficient, and the global-phase counterexample; reject stale outputs after
a failed cell; and check malformed math delimiters. They also test no-overwrite
behavior. The first targeted run caught a wrong relative code-map link
(1 failed, 5 passed); after correcting the link, the targeted run reported
6 passed in 23.81 s. No numerical benchmark was changed to force a pass.

The final structural audit verified 33 equation anchors,
20 implementation callables, 40 named tests,
126 local links, four valid source notebooks and 163 inventory-hash checks
(nested inventories repeat some files). [Audit JSON](../results/stage7-logs/package-verified.json).
The checker is a traceability and syntax tool, not a symbolic theorem prover.

Using the already-installed optional GUI runtime for a temporary **local-only**
rendering audit, all **207 LaTeX expressions** (68 display expressions)
rendered with zero KaTeX errors, exceptions, or display-equation overflows at
a 1200-pixel viewport. [Rendering audit](../results/stage7-logs/render-verified.json)
and [screenshot](../results/stage7-logs/render-energy-verified.png). This check
added no dependency to the notebook runner or qwave. The temporary server on
127.0.0.1:8502 was stopped after inspection. Other Markdown renderers must
support dollar-delimited LaTeX; structural balance alone cannot guarantee
that every third-party viewer has a math renderer.

## Exact verification commands

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.
The initial grouped acceptance commands, with return codes, full stdout/stderr
and timing, are in [executed-commands.json](../results/stage7-logs/executed-commands.json).
The full test suite passed after the code and notebooks were finalized; final
prose refinements were then rechecked with a fresh notebook run, structural
audit and live math render. No numerical source or notebook computation changed
after the full test run.

```sh
.venv/bin/python -c 'import sys,json; sys.path.insert(0,'"'"'docs/derivations'"'"'); from verification import verify_workspace_source; print(json.dumps(verify_workspace_source(),indent=2))'
.venv/bin/qwave doctor --dev
.venv/bin/qwave config-check examples/demo.json
.venv/bin/qwave demo --config examples/demo.json --output results/stage7-demo
.venv/bin/python docs/derivations/run_notebooks.py --output results/stage7-learning
.venv/bin/python docs/derivations/check_package.py --results results/stage7-learning --output results/stage7-logs/package-check.json
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/test_derivation_package.py
.venv/bin/python docs/derivations/run_notebooks.py --output results/stage7-learning-verified
.venv/bin/python docs/derivations/check_package.py --results results/stage7-learning-verified --output results/stage7-logs/package-verified.json
.venv/bin/python -m streamlit run results/stage7-logs/render_docs.py --server.port 8502
```

The temporary preview's first launch was blocked by the filesystem/network
sandbox's loopback restriction; the authorized localhost launch then succeeded.
No unresolved approval or authentication blocker remains. Package installation
was already present and was not repeated; all 36 imported Python/marker files
matched the workspace before verification. The first notebook run's Matplotlib
cache-location warning was resolved with a writable temporary cache.

## Source identity and limits

qwave package source hash: `ea6d46261236cc44fcd76325261a58d2d750b53f4497d7266a8aae54ab6b7aae`.
The workspace has no initial Git commit; the manifest correctly records a null
commit and a dirty working tree. Exact package files, learning sources, tests,
pyproject, configurations and outputs are hashed instead of inventing a commit.

Runtime versions:

```json
{
  "matplotlib": "3.11.2",
  "numpy": "2.5.5",
  "pip": "24.2",
  "pytest": "9.2.0",
  "python": "3.13.0",
  "qwave": "0.7.0",
  "qwave_source": "0.7.0",
  "scipy": "1.18.1",
  "setuptools": null
}
```

No implementation blocker remains for this educational stage. The notebooks
are not a new research comparison or a real-time Schrödinger PDE solver.
Mathematical checks do not validate the effective-mass approximation against
a material, calibrate gate voltages, verify a measured covariance, establish
novelty/priority, or prove reduced real-world failure probability. Those evidence
gaps are explicitly flagged in [references.md](derivations/references.md).

## Generated examples and exact configurations

[Scattering configuration](../results/stage7-learning-verified/01_scattering/config.json) ·
[Packet configuration](../results/stage7-learning-verified/02_packets/config.json) ·
[Covariance configuration](../results/stage7-learning-verified/03_covariance/config.json) ·
[Sensitivity configuration](../results/stage7-learning-verified/04_sensitivity_objective/config.json).

![Gaussian-barrier packet and separate fidelity metrics](../results/stage7-learning-verified/02_packets/packets.png)

The position curves are outgoing lead components at the saved observation time;
the spectral curves retain their transmitted probability, without spatial renormalization.

![Derivative noise floor and Taylor limitation](../results/stage7-learning-verified/04_sensitivity_objective/sensitivity-objective.png)

The strength sweep keeps the same educational draws and records both Taylor
and KL error. At large strength the first-order approximation fails visibly.
