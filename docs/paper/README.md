# Preparing an honest Phaseward paper

This stage prepares evidence and manuscript structure. It asserts no discovery
and writes no Results narrative. The bibliography is an initial primary-source
screening; full-text review and a verified novelty gap remain outstanding.

## Local workflow

Choose a completed frozen `experiment_suite` run before choosing favorable plots.
The exporter currently supports manifest version 2 and compatible recorded
analysis/plotting code, with a 256 MiB input/expanded-NPZ limit. It rejects older
or incomplete runs rather than guessing their schema. Explicitly failed checks
in a completed suite remain visible; they are not converted to passes.

```sh
qwave paper-export --run results/stage6-final-benchmark --output results/paper-benchmark-new
python3 results/paper-benchmark-new/verify_package.py
```

The destination must be new and disjoint from the source. There is intentionally
no overwrite flag. A failed export without `export_manifest.json` is incomplete.
Existing results, their manifests, raw data and seeds are never changed.

The package contains every inventoried original output, a figure index with
hashes, descriptive caption drafts, physical/algorithm tables, all paired and
descriptive statistics, constraint/search records, a reproducibility statement,
review and registration templates, and two LaTeX documents. `paper.tex` leaves
Results unfilled. `support.tex` contains the measured-data appendix; it does not
turn the benchmark into a finished scientific paper.

## What is checked

1. Strict JSON, safe paths, sizes and hashes for every input; matching config,
   exact seed registry, source identity, plan/freeze hashes and NPZ provenance.
2. Trial identifiers, partition counts, seeds and frozen gate vectors; validity
   flags; packet throughput/raw/aligned fidelity and delay from saved complex
   amplitudes; stored conservation arrays. No new forward solves are performed.
3. Every JSON/CSV cell, descriptive summaries, paired-bootstrap intervals and
   saved bootstrap arrays. Failed and undefined measurements stay explicit.
4. Every original PNG is reproduced pixel for pixel; SVGs must reproduce their
   geometry after timestamp and random resource-ID normalization. PDF bytes and
   page streams must match after creation-timestamp normalization. All formats
   are copied verbatim with their original hashes.
5. Every generated CSV is checked against its JSON records; original copies are
   rechecked after export. Export-time identity is kept separate from run identity.

The replay tolerances are floating-point reduction allowances, not claims about
physical accuracy. Timings are recorded historical values; numerical-convergence
forward solves are not rerun. Replaying the same implementation checks consistency,
not an independent physical derivation. If plot rendering or relevant code differs,
the exporter refuses a misleading match and asks for a compatible environment.

SHA-256 is an integrity check against an unsigned manifest, not an authorship or
pre-registration guarantee. The source snapshot/dependencies still need a durable
release for a paper. A benchmark whose scores have been inspected cannot become
a fresh confirmatory experiment. Fixed-case convergence is not evidence that all
optimized devices have converged, and the confidence intervals condition on the
frozen trained designs rather than repeated independent training campaigns.

## Editable source assets

Packaged assets live in [src/qwave/paper_assets](../../src/qwave/paper_assets/):

- [Matrix template](../../src/qwave/paper_assets/literature_matrix_template.csv),
  [screened matrix](../../src/qwave/paper_assets/literature_matrix.csv),
  [verification records](../../src/qwave/paper_assets/literature_sources.json).
- [Pre-registration template](../../src/qwave/paper_assets/preregistration_template.md).
- [Research-error checklist](../../src/qwave/paper_assets/research_checklist.md).
- [Conditional contributions](../../src/qwave/paper_assets/conditional_contributions.md).
- [Paper scaffold](../../src/qwave/paper_assets/paper.tex) and
  [verified bibliography](../../src/qwave/paper_assets/verified_references.bib).

Assets are installed with qwave, so export does not depend on running from this
checkout. All export calculations and the standalone integrity verifier work
offline on CPU. LaTeX compilation is optional and uses free local tools; no cloud
publishing account or paid service is required.

The [stage-8 validation record](../validation_stage8.md) gives the actual frozen
run, installed-source check, test output, figure/table checks, exact commands and
remaining research limitations. The compiled scaffold and support appendix are
linked there; the original experiment and earlier exports remain unchanged.
