# Phaseward stage 8: honest paper preparation and frozen-run export

Validation date: **2026-11-20**. Installed package: **qwave 0.8.0**. All work ran locally on CPU; no new runtime dependencies, cloud services, credentials or paid publishing tools were required.

## Delivered architecture

- `src/qwave/paper_audit.py`: read-only manifest/schema checks; frozen design, configuration and seed bindings; packet/statistical replay; exact figure replay.
- `src/qwave/paper_export.py`: new-directory support assembly, checked tables, captions, figure index, reproducibility statement and separate export manifest.
- `src/qwave/paper_assets/`: installed literature matrices/verification registry, five verified bibliography records, pre-registration/error-checklist/contribution templates and LaTeX scaffolds.
- `qwave paper-export --run <folder> --output <folder>`: CLI independent of Streamlit; existing outputs and source runs are never overwritten.

## Chosen frozen evidence

The demonstration uses `results/stage6-final-benchmark`, selected because it is the existing benchmark, before selecting scores or plots. No design, seed distribution, optimization or physics solve was rerun or tuned by export. The original manifest SHA-256 is `65275a3dfde7f3a2bc8be90f660a322001b69fafb65d0dd0768c5a395bafb1e4`. All 29 inventoried files plus the original manifest were copied byte for byte.

Final support package: [README](../results/stage8-paper-release/README.md), [verification](../results/stage8-paper-release/verification.json), [export inventory](../results/stage8-paper-release/export_manifest.json).

The recorded overall hypothesis classification remains **contradicts**. The stored D-versus-A comparison supports the declared benefit, while D-versus-B and D-versus-C contradict it. This is the existing conditional benchmark classification, not a new discovery, a universal result, or a freshly preregistered study. No favorable run replaced it.

## Actual checks

- 52 installed source/asset files matched the workspace byte for byte; `pip check` found no broken requirements.
- **248 tests passed** in the final installed-package run, including 16 paper-export tests. No tests were skipped. The exact pytest output is below.
- 196 trial packet records were recomputed from saved complex amplitudes, with throughput, raw/aligned fidelity, bounded lag and conservation kept separate.
- 42 paired comparisons and all 42 stored bootstrap arrays were recomputed; 548 candidate records, failure/budget statuses, constraints and all partitions were retained.
- Four figure groups, each PNG/SVG/PDF, matched the frozen data. PNG pixels matched exactly. SVG geometry matched after timestamp/resource-ID normalization. PDF page streams and all other bytes matched after creation-timestamp normalization. All copies retain their original hashes.
- Generated CSV/JSON tables were checked cell by cell; the standalone offline verifier passed on all 69 inventoried export files, including original-run bindings, before and after LaTeX compilation.
- Both LaTeX documents compiled locally with shell escape disabled, and all five citations resolved. `paper.tex` keeps Results explicitly unfilled. Final logs contain no overfull boxes or unresolved references/citations. The epstopdf warning about disabled shell escape is expected; no EPS conversion is used.

```text
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
................................                                         [100%]
248 passed in 111.54s (0:01:51)
```

The tests include real small frozen-run exports without forward solves, integrity and semantic tampering, wrong seeds, altered bootstrap arrays, substituted PDFs, unsafe paths, incomplete schemas, existing-output protection, offline verification and a completed but infeasible study whose missing comparisons stay unresolved. A development-test file-handle warning was fixed before acceptance. A rendered long-hash overflow was fixed; a fresh final export and full suite were then rerun. Printed comparison tables use eight significant display digits to avoid breaking numbers across lines; the CSV/JSON values retain full stored precision. Earlier development packages were left unchanged.

Compiled review copies (outside the immutable support inventory; [PDF hashes and page counts](../results/stage8-release-logs/compiled_documents.json)): [paper scaffold PDF](../results/stage8-latex-release/paper.pdf), [measured-data support PDF](../results/stage8-latex-release/support.pdf).

## Exact acceptance commands and outputs

The executable driver is [acceptance.py](../results/stage8-release-logs/acceptance.py). [executed_commands.json](../results/stage8-release-logs/executed_commands.json) records exact argument vectors, working directories, environment overrides, exit codes and elapsed times. Each command has a matching `.stdout.txt` and `.stderr.txt` in that directory. The driver removed `PYTHONPATH` and set a writable local `MPLCONFIGDIR`; compilation set `TEXINPUTS` and `BIBINPUTS` as recorded.

### wheel

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/stage8-release-wheels .
```

Exit 0; elapsed 1.113 seconds.

### install

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m pip install --no-index --no-deps --force-reinstall results/stage8-release-wheels/qwave-0.8.0-py3-none-any.whl
```

Exit 0; elapsed 0.441 seconds.

### source-match

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -c 'from pathlib import Path
import qwave,hashlib,json
source=Path('"'"'src/qwave'"'"');installed=Path(qwave.__file__).parent
paths=sorted(source.glob('"'"'*.py'"'"'))+[source/'"'"'py.typed'"'"']
paths += [p for p in (source/'"'"'paper_assets'"'"').rglob('"'"'*'"'"') if p.is_file() and p.suffix in {'"'"'.py'"'"','"'"'.md'"'"','"'"'.json'"'"','"'"'.csv'"'"','"'"'.bib'"'"','"'"'.tex'"'"'}]
assert {p.name for p in source.glob('"'"'*.py'"'"')} == {p.name for p in installed.glob('"'"'*.py'"'"')}
assert all(p.read_bytes()==(installed/p.relative_to(source)).read_bytes() for p in paths)
print(json.dumps({'"'"'package'"'"':str(installed),'"'"'version'"'"':qwave.__version__,'"'"'matched_files'"'"':len(paths),'"'"'files'"'"':{str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},indent=2))
'
```

Exit 0; elapsed 0.045 seconds.

### pip-check

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m pip check
```

Exit 0; elapsed 0.229 seconds.

### pytest

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python -m pytest -q
```

Exit 0; elapsed 112.129 seconds.

### doctor

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave doctor --dev
```

Exit 0; elapsed 0.651 seconds.

### config-check

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave config-check examples/demo.json
```

Exit 0; elapsed 0.369 seconds.

### demo

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave demo --output results/stage8-demo-release
```

Exit 0; elapsed 0.434 seconds.

### paper-export

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/qwave paper-export --run results/stage6-final-benchmark --output results/stage8-paper-release
```

Exit 0; elapsed 18.896 seconds.

### verify-package

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/verify_package.py
```

Exit 0; elapsed 0.043 seconds.

### paper-latex-1

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/manuscript`.

```sh
/Library/TeX/texbin/pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-latex-release paper.tex
```

Exit 0; elapsed 0.559 seconds.

### paper-bibtex

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-latex-release`.

```sh
/Library/TeX/texbin/bibtex paper
```

Exit 0; elapsed 0.096 seconds.

### paper-latex-2

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/manuscript`.

```sh
/Library/TeX/texbin/pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-latex-release paper.tex
```

Exit 0; elapsed 0.500 seconds.

### paper-latex-3

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/manuscript`.

```sh
/Library/TeX/texbin/pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-latex-release paper.tex
```

Exit 0; elapsed 0.503 seconds.

### support-latex-1

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/manuscript`.

```sh
/Library/TeX/texbin/pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-latex-release support.tex
```

Exit 0; elapsed 0.463 seconds.

### support-latex-2

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/manuscript`.

```sh
/Library/TeX/texbin/pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-latex-release support.tex
```

Exit 0; elapsed 0.471 seconds.

### verify-after-latex

Working directory: `/Users/baharyuksel/Documents/ChatGPT/Phaseward`.

```sh
/Users/baharyuksel/Documents/ChatGPT/Phaseward/.venv/bin/python /Users/baharyuksel/Documents/ChatGPT/Phaseward/results/stage8-paper-release/verify_package.py
```

Exit 0; elapsed 0.036 seconds.

## Scope and unresolved research work

There are no unresolved implementation or validation blockers for this export stage. The following are deliberately not claimed complete:

- The five paper identities, DOI/journal metadata and abstract-level findings were checked against primary publisher or author-uploaded records on 2026-11-20. This is an initial screening; full-text details, exhaustive prior-art coverage and a proposal-specific novelty gap remain unresolved. See the exported verification registry and matrix.
- The pre-registration document is an unfilled prospective template. Existing inspected benchmark seeds cannot serve as a new untouched confirmation set. Local hashes/timestamps are unsigned and do not prove external registration or authorship.
- The support package records historical source/environment identities but is not a complete archived historical source release. A publication requires durable code/data release and the remaining research decisions in the template.
- Same-implementation analysis replay establishes internal consistency, not independent solver correctness. Original convergence solves and timings are preserved, not rerun. Fixed first-case convergence does not certify every optimized design; inference is conditional on the recorded trained designs.
- Input support is intentionally limited to completed experiment-suite manifest v2 runs with compatible analysis/plotting sources, at most 256 MiB including expanded NPZ. Larger, older or differently rendered runs are rejected explicitly.
