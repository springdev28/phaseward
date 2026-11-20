# Executed shell commands — PROMPT 0

Working directory unless otherwise stated:
`/Users/baharyuksel/Documents/ChatGPT/Phaseward`.
Code and documentation were written with the editor's `apply_patch` tool.
Independent read-only checks sometimes ran concurrently. Commands below are
the actual shell inputs; installation retries are retained rather than hidden.

## Initial inspection

```sh
pwd; rg --files -g 'AGENTS.md' -g '!\.git' -g '!\.venv' -g '!node_modules' -g '!results' . /Users/baharyuksel/Documents/ChatGPT 2>/dev/null
```

```sh
ls -la
```

```sh
cat /Users/baharyuksel/.codex/plugins/cache/openai-curated-remote/google-drive/0.1.26/skills/google-drive/SKILL.md
```

```sh
for p in /AGENTS.md /Users/AGENTS.md /Users/baharyuksel/AGENTS.md /Users/baharyuksel/Documents/AGENTS.md /Users/baharyuksel/Documents/ChatGPT/AGENTS.md; do if [ -f "$p" ]; then printf '\n%s\n' "$p"; cat "$p"; fi; done
```

```sh
git status --short --branch; git log -1 --oneline; command -v python3; python3 --version; uname -m; command -v python3.11 python3.12 python3.13 python3.14 uv
```

`git log` reported no commits. Some explicitly probed Python executable names
were absent; `python3` resolved to Python 3.13.0, and the process was arm64.

```sh
cat /Users/baharyuksel/.codex/plugins/cache/openai-curated-remote/google-drive/0.1.26/skills/google-docs/SKILL.md
```

```sh
python3 -m pip --version; python3 -m pip list --format=columns; du -sh /Users/baharyuksel/Library/Caches/pip /Users/baharyuksel/.cache/uv 2>/dev/null
```

The cache probe ended with a nonzero status for the absent/unavailable pip cache.
No system package was changed. Drive folder listing and both document reads used
the Google Drive connector, not shell commands; see [source_review.md](source_review.md).

## Environment creation and installation

```sh
python3 -m venv .venv
```

```sh
source .venv/bin/activate
pip install -e '.[dev]'
```

The first installation failed because sandbox DNS/network restrictions prevented
retrieval of the isolated setuptools build dependency. The permitted retry was:

```sh
.venv/bin/python -m pip install --no-cache-dir -e '.[dev]'
```

This succeeded, including native arm64 numerical-library wheels and the editable
`qwave` console script. It installed into `.venv/` only.

## Test and CLI execution

```sh
source .venv/bin/activate
pytest
```

```sh
source .venv/bin/activate
qwave doctor --dev
qwave config-check examples/demo.json
MPLCONFIGDIR="$PWD/results/.matplotlib-cache" qwave demo --config examples/demo.json --output results/stage0-demo --plot
python -m pip check
```

```sh
git diff --check; git status --short --untracked-files=all; rg --files src tests docs examples
```

The initial diff check had no tracked diff because this started as an empty
repository. It is not presented as a lint check of untracked files.

```sh
.venv/bin/python -m pip freeze --all
```

```sh
cat results/stage0-demo/metrics.json; cat results/stage0-demo/manifest.json; git check-ignore results/stage0-demo/manifest.json .venv/pyvenv.cfg
```

## Wheel packaging

```sh
python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir --wheel-dir results/wheels .
```

This read the existing system setuptools installation to build a wheel offline;
it did not install or modify system packages. Output:
`results/wheels/qwave-0.1.0-py3-none-any.whl`.

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
import zipfile

wheel = Path('results/wheels/qwave-0.1.0-py3-none-any.whl')
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    required = ['qwave/cli.py', 'qwave/py.typed', 'qwave/scattering.py',
                'qwave-0.1.0.dist-info/licenses/LICENSE',
                'qwave-0.1.0.dist-info/entry_points.txt']
    assert all(name in names for name in required)
    entry_points = archive.read('qwave-0.1.0.dist-info/entry_points.txt').decode()
    assert 'qwave = qwave.cli:main' in entry_points
    print(f'Wheel verified: {wheel}; {len(names)} entries; console script and MIT license included.')
PY
```

Output:

```text
Wheel verified: results/wheels/qwave-0.1.0-py3-none-any.whl; 22 entries; console script and MIT license included.
```

## Final file and source audit

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib
import json

required = [
    'pyproject.toml', 'README.md', '.gitignore', 'LICENSE', 'AGENTS.md',
    'examples/demo.json', 'docs/architecture.md', 'docs/source_review.md',
    'docs/validation.md', 'docs/command_log.md',
]
assert all(Path(name).is_file() for name in required)
manifest = json.loads(Path('results/stage0-demo/manifest.json').read_text())
for name, digest in manifest['source']['files_sha256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
files = [Path(name) for name in required]
files += list(Path('src').rglob('*.py')) + list(Path('tests').rglob('*.py'))
for path in files:
    content = path.read_text()
    assert not content or content.endswith('\n'), path
    assert all(line == line.rstrip() for line in content.splitlines()), path
print('Final audit passed: required files exist, source hashes match the tested demo, and checked files have clean whitespace.')
PY
git status --short
git check-ignore results/stage0-demo/manifest.json .venv/pyvenv.cfg
```

## PROMPT 5 experiment-runner acceptance

The complete executed build, install, test, configuration, doctor, demo,
optimization, smoke and benchmark commands and actual outputs are recorded in
[stage-5 validation](validation_stage5.md). The machine-readable command log is
`results/stage5-final-logs/executed-commands.json`; its exact argument lists were
executed by `results/stage5-final-logs/acceptance.py`.

Final result bundles are `results/stage5-final-smoke` and
`results/stage5-final-benchmark`. The final audit independently checked hashes,
recomputed packet metrics from complex arrays, and verified the presentation-only
replay preserved all scientific arrays. Research profiles were not executed.

## PROMPT 6 optional local interface acceptance

The final installed-source verification, 226-test output, 24 sequential CLI
acceptance commands, browser/worker checks, output hashes and limitations are in
[stage-6 validation](validation_stage6.md). Exact final argument lists and exit
codes are recorded in `results/stage6-final-logs/executed-commands.json`; they were
executed by `results/stage6-final-logs/acceptance.py`. The integrity audit checked
11 bundles and 282 inventoried outputs. No research profile was launched.

The optional panel was verified with `.venv/bin/python -m streamlit run app.py`
at `http://127.0.0.1:8501`. The documented user entrypoint is
`streamlit run app.py`, with the project virtual environment activated.

## Derivation package and executable learning route

The seven chapters, four ordinary-Python notebooks, theory/code/test/figure map,
and six new tests are documented in [stage-7 validation](validation_stage7.md).
The full suite reported **232 passed in 93.36 s**. Final notebooks completed
22 numerical checks and produced eight PNG/SVG/PDF figures. A local renderer
checked 207 LaTeX expressions; final traceability and hash checks passed.

Exact grouped acceptance argument lists and stdout/stderr are saved in
`results/stage7-logs/executed-commands.json`. After final prose refinements:

```sh
.venv/bin/python docs/derivations/run_notebooks.py --output results/stage7-learning-verified
.venv/bin/python docs/derivations/check_package.py --results results/stage7-learning-verified --output results/stage7-logs/package-verified.json
```

The successful bundle is `results/stage7-learning-verified/`; earlier runs remain
available rather than being overwritten. The source notebooks call the actual
unchanged qwave library, and the runner needs neither Jupyter nor Streamlit.
The optional Streamlit installation was used only for a temporary localhost
rendering audit on port 8502, which was stopped after inspection. No research
profile, optimizer tuning, or held-out experiment was performed in this stage.
