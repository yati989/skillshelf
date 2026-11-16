# Personal-context workflow

The launcher resolves the Knowledge Base project from `--project`,
`KNOWLEDGE_BASE_PROJECT`, or the installed `project.json` pointer. The profile
root defaults to `~/.codex/personal-context`; `PERSONAL_CONTEXT_ROOT` or
`--root` selects an explicit isolated root.

## Readable profile

`profile.json` remains canonical for precise facts, evidence, and the separately
approved narrative record. `profile.md` renders that narrative's exact approved
wording. See [narrative.md](narrative.md) for drafting and approval. Fact changes
never automatically rewrite prose; review any affected passages separately.

`export-markdown` restores the approved narrative without inventing text or
changing approval history. An older profile without an approved narrative keeps
its existing Markdown until the user approves a replacement. If no Markdown or
approved narrative exists, initialization creates only an empty-profile notice.
Routine retrieval uses scoped `list` and `get` rather than the full portrait.

## Read relevant context

```text
python3 <skill>/scripts/context.py list
python3 <skill>/scripts/context.py list --category learning
python3 <skill>/scripts/context.py list --scope reading
python3 <skill>/scripts/context.py get teaching-style
```

`list` returns keys and routing metadata, not fact text or evidence. Retrieve
only keys relevant to the active task. Do not fetch restricted keys without a
direct task need.

## Review and propose

For a manual request to review chats, lessons, a date range, or files, first
follow [manual-review.md](manual-review.md) to resolve the scope, inspect available
evidence, and identify coverage limits. The user's review request replaces the
need for a separate workflow's completion signal; exact-change approval is still
required before applying additions, updates, or deletions.

Prepare a JSON payload with a `source` object and nonempty `changes` array:

```json
{
  "source": {
    "workflow": "reading-agent",
    "unit_id": "book-id-chapter-4"
  },
  "changes": [
    {
      "action": "add",
      "key": "reading-comparison-style",
      "fact": "Prefers comparisons tied to exact passages.",
      "category": "preferences",
      "scopes": ["global", "reading"],
      "sensitivity": "normal",
      "attribution": "user_statement",
      "confidence": "high",
      "evidence": "The user explicitly requested this during Chapter 4."
    }
  ]
}
```

Actions are `add`, `update`, or `delete`. Updates contain the complete proposed
replacement fact. Deletes contain `key` and `reason`. Attribution is one of
`user_statement`, `historical_observation`, or `assistant_inference`; every
proposal still requires approval. Sensitivity is `normal` or `restricted`.

Show the exact proposal to the user. A pending proposal may then be recorded:

```text
python3 <skill>/scripts/context.py propose /absolute/path/proposal.json
```

Only after explicit approval apply all or named keys:

```text
python3 <skill>/scripts/context.py approve proposal-id
python3 <skill>/scripts/context.py approve proposal-id --key approved-key
```

Reject all or named pending keys with a reason:

```text
python3 <skill>/scripts/context.py reject proposal-id --reason "User declined"
python3 <skill>/scripts/context.py reject proposal-id --key declined-key --reason "User declined"
```

For a mandatory review that finds nothing durable, record a payload containing
`source` and `reason`, then run:

```text
python3 <skill>/scripts/context.py record-no-change /absolute/path/review.json
```

Creating a checkpoint, accepting a deliverable, completing a chapter, or
approving one key does not approve any other profile change.
