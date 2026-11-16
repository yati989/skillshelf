# Shared reading workspace

## Starting and locating data

Run `python3 <skill-directory>/scripts/read.py context` first. The launcher resolves
the project from `--project`, `KNOWLEDGE_BASE_PROJECT`, installed `project.json`, or
the source checkout, in that order. Its default workspace is the resolved
project's `.kb-workspace`, not the current shell directory. `--root PATH` selects
an explicit workspace, including an isolated test workspace.

From the project checkout, equivalent commands are:

```bash
PYTHONPATH=src python3 -m knowledge_base.reading_cli --root .kb-workspace context
PYTHONPATH=src python3 -m knowledge_base.reading_cli --root .kb-workspace init
```

`context` is read-only and reports initialization, current self/wiki/session note
paths, metadata paths, revisions, content hashes, and the existing tutor-profile
pointer. Read relevant files from those paths. Retrieve approved current facts
through the separate `personal-context` skill; an absent fact means unknown, not
permission to invent background. Initialization is idempotent and preserves
existing tutor subjects and reading evidence.

## Data ownership

| Location within `.kb-workspace` | Purpose |
| --- | --- |
| `library/catalog/` | Resource identities, versions, extraction status, original locations |
| `library/originals/` | Content-addressed original reading files |
| `library/extracted/` | Versioned structured blocks and whole/chapter Markdown views |
| `wiki/` | Current authored concept, work, question, and comparison notes |
| `sessions/` | Curated discussion outcomes and resumption points |
| `self/` | Reading evidence: attributed statements, historical summaries, and hypotheses; not the current profile |
| `records/reading-notes/` | Durable citation metadata and revision information |
| `records/reading-revisions/` | Prior authored notes and reconciled manual edits |
| `records/reading-log.jsonl` | Workspace change metadata, not personal activity history |
| `records/reading-locks/` | Local coordination for concurrent source and note updates |
| `indexes/` | Derived navigation and lexical search data |
| `subjects/` | Existing tutor-owned subject, track, assessment, and progress records |

Sources and authored notes are durable. Revision metadata is also durable; it is
not a cache. Preserve it with its Markdown. The project ignores `.kb-workspace`
in Git. No raw Google/YouTube export or activity database belongs in this layout.

## Prepare and read a source

The command names below follow `python3 <skill-directory>/scripts/read.py`:

```text
resources
ingest /absolute/path/book.pdf --title "Book title" --author "Author"
ingest /absolute/path/revised-book.pdf --title "Book title" --source-id existing-id
reuse /absolute/project/.kb-workspace/subjects/subject/sources/structured/book.json
search "the question or terms" --source-id returned-source-id --limit 3
read returned-source-id --section "Exact chapter or heading"
read returned-source-id --section b00002 --max-chars 16000
read returned-source-id --source-hash returned-full-hash
review returned-source-id --reason "What was inspected and why the extraction is usable"
```

`ingest` supports local PDF, Markdown, text, HTML, VTT, and SRT. It preserves
originals and versioned extraction, and returns a catalog resource with
`source_id`, `current_hash`, and `versions`. Repeating identical content is a
no-op; a new version under the same ID preserves earlier citation targets.
Ingestion is evidence preparation, not a record that the reader finished a book.

For PDFs, this is the standard PDF-to-Markdown path shared with the
source-grounded tutor. It writes a versioned `full.md` and chapter views under
`library/extracted/<source-id>/<source-hash>/chapters/`; use those views for
chapter reading and precise line or paragraph/block pointers. Preserve the PDF
as the authority for printed page numbers, figures, tables, footnotes, and any
layout the extraction may have flattened. Prefer `reuse` when the tutor has
already prepared the same source. Run a separate converter only to diagnose or
repair a failed or materially inaccurate shared extraction.

`reuse` accepts an existing structured tutor document inside this workspace's
`subjects/`. It snapshots the extraction and records its existing location,
without copying the original book or changing the tutor's manifest or phase.
The skill makes no assumptions about the subjects already present.

`read` returns serialized blocks with IDs, exact locations, source hash, heading
paths, extraction status, warnings, and a `truncated` flag. `--section` matches an
exact heading, full heading path separated by ` > `, or block ID. If output is
truncated, retrieve narrower sections/blocks, use bounded search, or read the
listed chapter Markdown in bounded portions. Do not infer unseen conclusions.

`search` retrieves only ready current source versions. It preserves block IDs
and exact source-version hashes. Inspect the passage before citing it. `read`
also exposes uncertain extraction so it can be inspected; a warning is not a
review. Run `review` only after checking the relevant source representation.
The result and change log identify the accepted version with `reviewed_hash`;
if another import intervened, this can differ from the current source version.
An empty/failed extraction cannot be accepted and must be repaired or replaced.
Parser repair/reprocessing of identical content is not automated in this first
version; preserve the failed record and diagnose before modifying artifacts.

For complete chapter reading, follow [chapter-coverage.md](chapter-coverage.md).
Neither ingestion nor a successful `read` verifies that every substantive item
has been explained. Track the inspected ranges, source-to-part map, remaining
items, and extraction gaps in the session note's `body`. Use existing commands;
the helper does not maintain or validate semantic coverage automatically.

For a pasted passage, preserve the supplied text in a local `.md` or `.txt` file
before ingestion; do not add unsupported author or edition metadata. If durable
saving is declined, prepare in a temporary directory and pass an isolated
`--root`; do not initialize or save notes in the permanent workspace. Existing
Markdown can be ingested as-is after checking its content and boundaries.

## Save a note

Prepare a JSON payload with file-editing tools, then run:

```text
save-note /absolute/path/payload.json
```

Use these fields:

| Field | Meaning |
| --- | --- |
| `kind` | `session`, `wiki`, or `self` |
| `id` | Stable lowercase ID, such as `uncertainty-and-explanation`; reuse it when updating |
| `title` | Human-readable title |
| `body` | Curated Markdown; attribute positions and keep unresolved questions visible |
| `citations` | Optional array of exact source references as described below |
| `links` | Optional existing note paths, e.g. `sessions/first-reading.md` |
| `basis` | Provenance/context; required for self notes |
| `attribution` | Required for self: `user_statement`, `historical_observation`, or `assistant_inference` |
| `category` | Optional self area; `worldview`, `background`, and `preferences` require `user_statement` |
| `expected_revision` | Required when updating; copy the current revision from context/metadata |
| `expected_content_hash` | Supply the observed Markdown hash when reconciling manual edits |

Each citation has `source_id`, `source_hash` (the complete returned SHA-256), and
`block_id`. An optional `quote` must occur in that block, allowing whitespace
normalization. The tool supplies the verified location. Multiple sources are
allowed. The tool validates identity and quote matching, not whether an
interpretation logically follows: that remains the reader/assistant's judgment.

An original discussion insight can link to its session and identify its basis
instead of pretending it is a quotation from a book. Historical self summaries
identify the analyzed export, covered period, analysis date, and limitations in
`basis` and their body; they do not need imported raw event records.

The helper writes readable current Markdown plus citation metadata and prior
revisions. Updating an ID requires reading the existing note first. A stale
revision is an error. If a user edited Markdown directly, context reports
`modified: true` and its current hash. Read and preserve that edit, then supply
both the current revision and `expected_content_hash`; the manual version is
retained during reconciliation. An untracked existing file is not overwritten.

When correcting a personal note, mark what is current in the body and retain the
older interpretation only as dated history. Read related notes for dependencies
that also need correction. Do not update the legacy tutor profile in parallel.

## Validate development changes

Run the existing and reading-specific tests from the project checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the platform's skill frontmatter validator against this skill folder when
available. Forward-test the installed launcher from an unrelated directory with
an explicit isolated `--root`. Useful checks are a real passage lookup, precise
citation, saved session, revised personal statement, and a fresh-session resume.
Testing must not add fictional user statements or fixture sources to the real
personal workspace.
