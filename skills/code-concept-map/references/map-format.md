# Map format

Author UTF-8 JSON in this shape. The example is illustrative: replace its claims and paths with inspected repository evidence.

```json
{
  "schema_version": 1,
  "repository": {
    "name": "example-project",
    "revision": "abc1234 + working-tree changes",
    "summary": "A small client that processes records from an HTTP service."
  },
  "coverage": {
    "summary": "Inspected the client, processing code, tests, and package configuration.",
    "inspected": ["src/", "tests/", "pyproject.toml"],
    "excluded": ["Generated files and installed dependencies"],
    "gaps": ["Optional plugins were not inspected"]
  },
  "nodes": [
    {
      "id": "python",
      "label": "Python",
      "kind": "category",
      "summary": "The language used for the client and processing logic.",
      "children": [
        {
          "id": "python-generators",
          "label": "Generators",
          "kind": "concept",
          "summary": "Functions that produce values one at a time, pausing between values.",
          "usage": "The client exposes incoming records as a sequence that callers can consume gradually.",
          "confidence": "observed",
          "evidence": [
            {"path": "src/client.py", "start": 12, "end": 18,
             "note": "The generator yields each decoded record."}
          ],
          "related": ["lazy-evaluation"],
          "children": []
        }
      ]
    }
  ]
}
```

The example's `lazy-evaluation` link requires a matching node in the completed map; omit the link if no such node is supported.

- `schema_version`: integer `1`.
- `repository`: required nonempty strings `name`, `revision`, `summary`. Do not put a local absolute path or remote credential in these fields.
- `coverage`: required `summary` string and arrays of strings `inspected`, `excluded`, `gaps`. An empty gaps array means no known gap within the described inspection scope, not proof of exhaustive analysis.
- `nodes`: nonempty array of top-level category nodes. A category requires supported descendants.
- All nodes: unique stable `id` matching `[a-z0-9][a-z0-9-]*`, nonempty `label` and `summary`, `kind` (`category` or `concept`), optional `children` array and optional `related` array of other existing IDs. The renderer supplies empty arrays when omitted. Avoid redundant nodes solely to reach a particular depth.
- Concept nodes: required nonempty `usage`, `confidence` (`observed` or `inferred`), and nonempty `evidence` array. When inferred, state the interpretive reasoning in usage or evidence notes.
- Evidence: required repository-relative POSIX `path`, one-based integer `start` and `end`, and nonempty `note`. Ranges must exist and contain at most 16 lines each; use several focused examples if needed. Paths must resolve inside the repository, including symlinks. Choose UTF-8 text files. Optional `redacted: true` retains the citation and note but embeds no excerpt. Do not quote the sensitive content in the note either.
- `snippet` is renderer-owned; the renderer replaces supplied snippets with the cited source. The saved JSON contains the resulting snippets for portability. It can be edited and passed to the renderer again, which refreshes citations from source.
- `generated_at` and `map_id` are renderer-owned snapshot metadata. Do not author them.

The renderer checks structure, node/link integrity, paths, and line ranges. It does not infer concepts or verify that a code excerpt logically supports an explanation. That remains the analyzing agent's responsibility.
