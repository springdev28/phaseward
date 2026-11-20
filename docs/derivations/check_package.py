"""Check teaching links, equations, code mappings, notebooks and optional result hashes.

This is a structural/traceability check, not a symbolic proof or a LaTeX renderer.
Actual numerical checks run in pytest and the notebooks; visual rendering is
recorded separately in docs/validation_stage7.md.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from verification import GUIDE, ROOT, sha256_file, write_json


def prose(text: str) -> str:
    """Exclude fenced and inline code from mathematical and link syntax checks."""
    no_fences = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", no_fences)


def math_blocks(text: str) -> list[dict[str, Any]]:
    """Extract paired dollar-delimited math; reject mismatched pairs and braces."""
    content = prose(text)
    blocks = []
    opened: re.Match[str] | None = None
    for token in re.finditer(r"(?<!\\)\${1,2}", content):
        if opened is None:
            opened = token
            continue
        if token.group() != opened.group():
            raise ValueError("Inline/display math delimiters are crossed")
        value = content[opened.end():token.start()]
        if not value.strip():
            raise ValueError("Empty math expression")
        depth = 0
        for brace in re.finditer(r"(?<!\\)[{}]", value):
            depth += 1 if brace.group() == "{" else -1
            if depth < 0:
                raise ValueError("Unmatched closing math brace")
        if depth:
            raise ValueError("Unmatched opening math brace")
        stack = []
        for env in re.finditer(r"\\(begin|end)\{([^}]+)\}", value):
            if env.group(1) == "begin":
                stack.append(env.group(2))
            elif not stack or stack.pop() != env.group(2):
                raise ValueError("Mismatched LaTeX environment")
        if stack:
            raise ValueError("Unclosed LaTeX environment")
        blocks.append({"display": opened.group() == "$$", "latex": value.strip()})
        opened = None
    if opened is not None:
        raise ValueError("Unclosed math delimiter")
    return blocks


def _callable(name: str) -> Any:
    parts = name.split(".")
    obj = importlib.import_module(".".join(parts[:2]))
    for part in parts[2:]:
        obj = getattr(obj, part)
    if not callable(obj):
        raise TypeError(f"Mapped implementation is not callable: {name}")
    return obj


def check(results: Path | None = None) -> dict[str, Any]:
    """Return counts or fail on a broken link, code name, figure or provenance hash."""
    math_count = 0
    files = sorted(GUIDE.glob("*.md"))
    local_links = 0
    anchors: set[str] = set()
    for path in files:
        content = path.read_text(encoding="utf-8")
        math_count += len(math_blocks(content))
        ids = re.findall(r'<a id="([^"]+)"></a>', content)
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate equation anchor in {path.name}")
        anchors.update(path.name + "#" + value for value in ids)
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", prose(content)):
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue  # External references were verified separately; never need network to run.
            linked = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not linked.is_file():
                raise FileNotFoundError(f"{path.name}: broken local link {target}")
            if url.fragment.startswith("eq-"):
                marker = '<a id="' + url.fragment + '"></a>'
                if marker not in linked.read_text(encoding="utf-8"):
                    raise ValueError(f"Missing equation anchor: {target}")
            local_links += 1
    entries = json.loads((GUIDE / "code-map.json").read_text())
    mapped = set()
    functions = set()
    tests = set()
    figures = set()
    for entry in entries:
        for equation in entry["equations"]:
            if equation["link"] not in anchors:
                raise ValueError(f"Missing mapped equation: {equation}")
            mapped.add(equation["link"])
        for function in entry["functions"]:
            _callable(function)
            functions.add(function)
        for test in entry["tests"]:
            file, name = test.split("::")
            tree = ast.parse((ROOT / file).read_text())
            definitions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
            if name not in definitions or not name.startswith("test_"):
                raise ValueError(f"Unknown mapped test: {test}")
            tests.add(test)
        figures.update(entry["figures"])
    if anchors != mapped:
        raise ValueError(f"Unmapped equation anchors: {sorted(anchors - mapped)}")
    notebooks = sorted((GUIDE / "notebooks").glob("*.ipynb"))
    code_cells = 0
    for notebook in notebooks:
        doc = json.loads(notebook.read_text())
        if doc["nbformat"] != 4 or doc["nbformat_minor"] != 5:
            raise ValueError("Expected nbformat 4.5")
        ids = [cell["id"] for cell in doc["cells"]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate cell id: {notebook.name}")
        for index, cell in enumerate(doc["cells"]):
            if cell["cell_type"] == "code":
                code_cells += 1
                if cell["execution_count"] is not None or cell["outputs"]:
                    raise ValueError("Source notebooks must be clean; executed copies live in results/")
                compile("".join(cell["source"]), f"{notebook.name}:{index}", "exec")
            else:
                math_count += len(math_blocks("".join(cell["source"])))
    checked_hashes = 0
    if results is not None:
        results = results.resolve()
        main = json.loads((results / "manifest.json").read_text())
        if main.get("status") != "complete":
            raise ValueError("Results do not have a complete manifest")
        for path in [results / "manifest.json", *sorted(results.glob("*/manifest.json"))]:
            manifest = json.loads(path.read_text())
            for relative, expected in manifest["inventory"].items():
                target = (path.parent / relative).resolve()
                if not target.is_relative_to(path.parent.resolve()) or not target.is_file():
                    raise ValueError(f"Unsafe or missing inventory file: {relative}")
                if target.stat().st_size != expected["bytes"] or sha256_file(target) != expected["sha256"]:
                    raise ValueError(f"Result hash mismatch: {target}")
                checked_hashes += 1
        for figure in figures:
            for extension in (".png", ".pdf", ".svg"):
                path = (results / figure).with_suffix(extension)
                if not path.is_file() or path.stat().st_size == 0:
                    raise FileNotFoundError(f"Missing mapped figure: {path}")
    return {"status": "passed", "markdown_files": len(files), "local_links": local_links,
            "equation_anchors": len(anchors), "math_expressions": math_count,
            "mapped_functions": len(functions), "mapped_tests": len(tests), "mapped_figures": len(figures),
            "notebooks": len(notebooks), "code_cells": code_cells, "checked_inventory_hashes": checked_hashes,
            "limit": "Structural and traceability checks; not symbolic proof or a renderer"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output", type=Path, help="Save a new JSON check report")
    args = parser.parse_args()
    result = check(args.results)
    if args.output:
        if args.output.exists():
            raise FileExistsError(args.output)
        write_json(args.output, result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
