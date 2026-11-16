#!/usr/bin/env python3
"""Validate an evidence-backed concept tree and render a portable offline viewer."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value, where):
    require(isinstance(value, str) and value.strip(), f"{where}: expected nonempty text")
    return value


def string_list(value, where):
    require(isinstance(value, list), f"{where}: expected an array")
    for item in value:
        nonempty(item, where)
    return value


def prepare_map(raw, repo):
    require(isinstance(raw, dict), "Map must be an object")
    data = deepcopy(raw)
    require(type(data.get("schema_version")) is int and data["schema_version"] == 1,
            "schema_version must be 1")
    repository = data.get("repository")
    require(isinstance(repository, dict), "repository must be an object")
    for key in ("name", "revision", "summary"):
        nonempty(repository.get(key), f"repository.{key}")
    coverage = data.get("coverage")
    require(isinstance(coverage, dict), "coverage must be an object")
    nonempty(coverage.get("summary"), "coverage.summary")
    for key in ("inspected", "excluded", "gaps"):
        string_list(coverage.get(key), f"coverage.{key}")
    roots = data.get("nodes")
    require(isinstance(roots, list) and roots, "nodes must be a nonempty array")
    repo = Path(repo).resolve(strict=True)
    require(repo.is_dir(), "--repo must be a directory")
    seen, links, source_cache = set(), [], {}

    def evidence(item, where):
        require(isinstance(item, dict), f"{where}: evidence must be an object")
        raw_path = nonempty(item.get("path"), f"{where}.path")
        relative = PurePosixPath(raw_path)
        require(not relative.is_absolute() and ".." not in relative.parts
                and "\\" not in raw_path, f"{where}: expected a repository-relative path")
        source = (repo / str(relative)).resolve(strict=True)
        try:
            source.relative_to(repo)
        except ValueError as exc:
            raise ValueError(f"{where}: source resolves outside repository") from exc
        require(source.is_file(), f"{where}: source is not a file")
        if source not in source_cache:
            source_cache[source] = source.read_text(encoding="utf-8").splitlines()
        lines = source_cache[source]
        start, end = item.get("start"), item.get("end")
        require(type(start) is int and type(end) is int,
                f"{where}: start/end must be integers")
        require(1 <= start <= end <= len(lines),
                f"{where}: invalid lines {start}-{end}; file has {len(lines)} lines")
        require(end - start < 16, f"{where}: use excerpts of at most 16 lines")
        nonempty(item.get("note"), f"{where}.note")
        require(type(item.get("redacted", False)) is bool, f"{where}.redacted must be boolean")
        item["path"] = relative.as_posix()
        item["snippet"] = "" if item.get("redacted") else "\n".join(lines[start - 1:end])

    def visit(node, depth=0):
        require(isinstance(node, dict), "Each node must be an object")
        ident = nonempty(node.get("id"), "node.id")
        require(re.fullmatch(r"[a-z0-9][a-z0-9-]*", ident), f"Invalid node ID: {ident}")
        require(ident not in seen, f"Duplicate node ID: {ident}")
        seen.add(ident)
        for key in ("label", "summary"):
            nonempty(node.get(key), f"{ident}.{key}")
        kind = node.get("kind")
        require(kind in ("category", "concept"), f"{ident}: invalid kind")
        require(depth > 0 or kind == "category", "Top-level nodes must be categories")
        children = node.setdefault("children", [])
        require(isinstance(children, list), f"{ident}.children must be an array")
        refs = string_list(node.setdefault("related", []), f"{ident}.related")
        links.extend((ident, ref) for ref in refs)
        proofs = node.setdefault("evidence", [])
        require(isinstance(proofs, list), f"{ident}.evidence must be an array")
        if kind == "category":
            require(children, f"{ident}: categories need supported descendants")
        else:
            nonempty(node.get("usage"), f"{ident}.usage")
            require(node.get("confidence") in ("observed", "inferred"),
                    f"{ident}: confidence must be observed or inferred")
            require(proofs, f"{ident}: every concept needs evidence")
        for i, item in enumerate(proofs):
            evidence(item, f"{ident}.evidence[{i}]")
        for child in children:
            visit(child, depth + 1)

    for root in roots:
        visit(root)
    for ident, ref in links:
        require(ref in seen and ref != ident, f"{ident}: invalid related link {ref}")
    data.pop("map_id", None)
    data.pop("generated_at", None)
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True)
    data["map_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    data["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return data


def embedded_json(data):
    # JSON lives in a script element; prevent source text from ending that element.
    return (json.dumps(data, ensure_ascii=False).replace("&", "\\u0026")
            .replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render(data):
    template = Path(__file__).resolve().parent.parent / "assets" / "viewer.html"
    html = template.read_text(encoding="utf-8")
    token = "__CONCEPT_MAP_DATA__"
    require(html.count(token) == 1, "Viewer template must contain exactly one data placeholder")
    return html.replace(token, embedded_json(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Concept map JSON drafted from inspected code")
    parser.add_argument("--repo", required=True, type=Path, help="Root for verifying source evidence")
    parser.add_argument("--output", required=True, type=Path, help="Destination HTML path")
    args = parser.parse_args()
    try:
        require(args.output.suffix.lower() == ".html", "--output must end in .html")
        data = prepare_map(json.loads(args.input.read_text(encoding="utf-8")), args.repo)
        html = render(data)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
        json_path = args.output.with_suffix(".json")
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Created {args.output.resolve()}")
        print(f"Created {json_path.resolve()}")
    except (ValueError, OSError, RecursionError) as exc:
        print(f"Map error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
