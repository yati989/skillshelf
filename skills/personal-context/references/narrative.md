# The narrative personal profile

Write `profile.md` as a connected, memory-like account of what is known about the
user. A simple title and flowing paragraphs are enough. Avoid broad category
headings, key-by-key entries, inventories, and a fixed template. Let the evidence
determine the emphasis and length. Integrate specific facts with the larger
picture: goals, values, circumstances, relationships, recurring emotional
responses, tensions, and changes over time when the selected evidence supports
those connections. This is a revisable understanding of a person.

Reasonable interpretations are welcome in a proposal. Make their status clear in
the wording: distinguish explicit statements, observed patterns, and possible
explanations. Use phrases such as “has described,” “seems to,” or “one possible
pattern” where needed. Preserve contradictory evidence and exceptions rather
than constructing a neat personality story. Do not diagnose, invent motives,
attribute other people's experiences to the user, or treat reading a book as
agreement with it. Do not hide all personal understanding behind a list of
verifiable facts; explain meaningful connections with appropriate uncertainty.

Use the relevant approved facts and the substantive evidence within the user's
selected review scope. Support broader connections with identifiable evidence.
Keep source locations, uncertainty, and sensitivity in the proposal's evidence;
the prose should remain readable. Precise facts retain their own semantic keys
and individual approval. An interpretation approved in the narrative is still
an interpretation, not an independently established fact.

## Propose and approve

Show the full exact replacement prose and briefly explain the important changes
and supporting evidence outside it. Save the draft outside the current profile
until approved. A request to change this skill, a chapter's `Done`, approval of a
review scope, or approval of factual keys does not approve the portrait.

Use the existing proposal/approval interface with a separate reserved key:

```json
{
  "source": {"workflow": "personal-context-manual-review", "scope": "selected discussions"},
  "changes": [
    {
      "action": "replace-narrative",
      "key": "profile-narrative",
      "markdown": "<the complete exact proposed Markdown>",
      "sensitivity": "normal",
      "evidence": "<source locations and dates; distinguish statements, observations, and tentative interpretations>"
    }
  ]
}
```

Run `context.py propose /absolute/path/proposal.json` to record it pending.
Only after the user explicitly approves that wording, run
`context.py approve proposal-id --key profile-narrative`. Use `reject` for a
declined draft. Mixed batches may include ordinary keyed facts, but approval of
one key never approves another. If approval is ambiguous, resolve it before writing.

The approved prose and its provenance live in JSON's optional `narrative` record;
`facts` remains the precise fact collection. Approval writes immutable before/after
history and exports the exact approved prose to `profile.md`. This keeps one
canonical approved store and a readable narrative rather than competing profiles.
`list` exposes narrative metadata only; `get profile-narrative` retrieves it when
needed. Mark the entire narrative `restricted` if it contains restricted material.

For narrative removal, propose action `delete-narrative`, key
`profile-narrative`, and nonempty `evidence` explaining the removal. Apply only
after explicit approval. The Markdown then contains only an empty-profile notice.
When a factual correction or deletion also affects the prose, show both changes
for approval so a removed or outdated claim does not linger in the portrait.
Do not silently rewrite unaffected paragraphs or repopulate a deleted portrait.

Initialization, approved fact changes, tutor imports, and `export-markdown` only
render already approved narrative wording; they never generate a new portrait.
Legacy profiles without a narrative record retain their existing Markdown until
an exact replacement is approved. Never promote that legacy fact list or an
existing unapproved draft into the narrative record automatically.
