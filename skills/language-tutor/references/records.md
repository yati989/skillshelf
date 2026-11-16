# Durable course records

## Location and helper

Install skill instructions separately from learner data. Agree a workspace root; one directory per course might be `<root>/spanish-travel/`. Do not initialize a course merely because the skill is being installed. Config uses the actual selected language and goals, not guessed defaults.

The standard-library helper `scripts/course.py` stores one readable UTF-8 `course.json` per course: immutable config and an append-only list of timestamped records/checkpoints. Atomic replacement and a writer lock prevent partial saves; optimistic revision checks reject stale writers. It supports macOS/Linux (uses `fcntl`). It does not require the knowledge-base application or external packages.

This is a storage helper, not an evaluator or approval authority. It validates unique IDs, append-only history, approval references, basic fields, and approved plans for teaching checkpoints. The tutor must verify actual learner authorization, source preparation, standalone `Done`, evidence, rubric judgments, and final-course coverage. Saving a result does not certify its correctness. Never edit `course.json` directly to repair or erase history; preserve the original, explain corruption, and restore from an available backup if needed.

Commands (substitute real absolute paths; invoke from the installed skill):

```sh
python3 ~/.agents/skills/language-tutor/scripts/course.py --course /absolute/course/path init --config /absolute/config.json
python3 ~/.agents/skills/language-tutor/scripts/course.py --course /absolute/course/path show
python3 ~/.agents/skills/language-tutor/scripts/course.py --course /absolute/course/path save --event /absolute/events.json --expected-revision 0
python3 ~/.agents/skills/language-tutor/scripts/course.py --course /absolute/course/path show --kind assessment --id assessment-l1-v1
python3 ~/.agents/skills/language-tutor/scripts/course.py --course /absolute/course/path show --history
```

Read `show` first and use its revision. A save accepts one event or a list saved as one transaction. The revision increases once per event. If any event fails validation, no event in the batch is written. On a stale revision, reread and reconcile; never blindly retry a previous mutation. Verify the returned revision/checkpoint, and inspect the relevant saved record when needed, before claiming success. On a failed save say what remains unsaved.

## Config and events

Config requires `course_id` (stable ASCII ID), `language`, `variety`, `explanation_language`, and nonempty `goals` list. Add timezone, starting self-report, script preference, and session preferences when actually established. Keep later config corrections in a `decision` record referencing the original; the effective settings include those decisions. Changing the language/variety substantially usually warrants a separate course.

A record event:

```json
{
  "type": "record",
  "kind": "session",
  "id": "session-2026-10-28-01",
  "data": {
    "lesson_id": "l1",
    "summary": "Practised introducing oneself; assignment unfinished.",
    "evidence_type": "typed"
  }
}
```

IDs use letters/digits/dot/underscore/hyphen, up to 128 characters. Each `(kind, id)` is unique. Updates are new records with `data.supersedes` referencing the previous ID of the same kind; original records remain available. The helper does not merge superseding data: write a complete replacement judgment and treat it as current, preserving its predecessor as history. Do not supersede assessment packets or finalized results to improve a score; create new attempts/results instead.

Supported record kinds and tutor-required contents:

| Kind | Contents |
| --- | --- |
| `source` | Candidate identity/version/variety, role, URL/path, access and inspection status. |
| `source-set` | `source_ids` referencing saved sources; rationale and coverage. |
| `source-status` | Source ID, acquisition/preparation/quality outcome, exact artifact locations and retrieval date. |
| `approval` | `target_kind` (source/source-set/plan), `target_id`, `decision` (approved/rejected/deferred), `learner_evidence` quoting or locating actual learner direction. |
| `placement` | Task, actual response/sample, modality, support, bounded starting judgment. |
| `plan` | `source_set_id`, version, core/deferred goals, ordered lessons/abilities/sources, assignments, review, criteria and modalities, cumulative assessment. |
| `lesson` | Plan/lesson ID, parts, material taught, generated examples, source locations, recap, teaching status; for closure include the actual standalone Done signal and its provenance. |
| `assignment` | Lesson/goal, scenario/roles/inputs, allowed support, stopping condition. |
| `assessment` | Frozen lesson or cumulative packet described in practice-and-assessment.md; never overwrite after delivery begins. |
| `attempt` | Stable activity/attempt ID, assignment or assessment ID, observed exchange segment, exact learner response where available, modality, assistance, segment order and pending turn. Separate IDs for segments preserve a live attempt. |
| `result` | Assessment/attempt IDs, criterion-level evidence/status, assistance, outcome, missing dimensions, feedback. Finalized once per attempt; later retesting uses another attempt. |
| `ability` | Ability/dimension ID, introduced/practising/demonstrated/retained/unassessed, evidence IDs, rationale/date, superseded judgment if any. |
| `review` | Target, supporting evidence IDs, due date or lesson trigger, activity, open/completed/deferred state. |
| `session` | Compact recap, observations versus learner report, relevant record IDs, unresolved items. |
| `decision` | Learner-directed pause, deferral, assessment decline, configuration correction, or other scope decision, with actual evidence. |

Do not duplicate entire copyrighted source works in the event log; retain source artifacts separately in the agreed workspace and cite precise locations. Do not store raw audio by default or manufacture verbatim transcripts from memory. Records can contain tutor-only scenario details; do not display hidden answers while testing.

Each source requires individual approval before a final source-set approval. A plan must reference an approved source set before plan approval. `learner_evidence` documents a real decision; the helper cannot obtain or infer permission. A new approval record may change a prior decision without erasing it. If an approved source set is later withdrawn, stop using affected material and reconcile the plan even though historical plan approval remains in the log.

## Exact checkpoints

```json
{
  "type": "checkpoint",
  "data": {
    "phase": "lesson",
    "plan_id": "plan-v1",
    "lesson_id": "l1",
    "part_id": "p4",
    "activity_id": "assignment-l1-attempt-1",
    "mode": "conversation",
    "evidence_type": "typed",
    "next_step": "Await learner reply to the shopkeeper's alternative.",
    "pending_prompt": "The small size is unavailable. Would you like a large one?",
    "support_given": [],
    "record_ids": ["assignment-l1", "turn-l1-03"]
  }
}
```

Phases: `setup`, `research`, `planning`, `lesson`, `assessment`, `review`, `paused`, `course-complete`. Modes: `coaching`, `conversation`, `assessment`, `text`. Evidence types: `live_audio`, `audio_recording`, `transcript`, `typed`, `learner_report`, `none`. Phase, mode, evidence_type, and a concrete next_step are required. Teaching/review/completion checkpoints also require an approved plan_id. An assessment checkpoint additionally requires an existing assessment_id and activity_id.

After plan approval without an explicit start instruction, use a `planning` checkpoint with the approved `plan_id`, a next step such as ‘Await explicit instruction to start Lesson 1’, and no learner practice prompt or teaching activity. Prepared lesson content is not taught material or ability evidence.

Save phase, lesson/part, current activity/attempt, pending prompt, support already given, and next action. For a pause include `resume_phase`. The global checkpoint is navigation; `activity_checkpoints` retains the latest checkpoint per activity, so switching lessons or assessments does not erase another pending turn. Always name assessment and attempt explicitly in evidence/results. Load that activity checkpoint when switching back and save a new global checkpoint to select it. Never route by a global pointer alone.

A useful save batch contains the new attempt segment, session or ability/review updates when justified, then the checkpoint. Checkpointing is permitted before Done and does not close teaching, pass an assessment, or update the global personal profile. Persist no more personal detail than needed to resume and evaluate the activity.
