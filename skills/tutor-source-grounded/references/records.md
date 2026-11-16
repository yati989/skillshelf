# Durable record requirements

Read this reference before generating JSON payloads or curated chapters.

## Source candidate

Every proposal needs:

- stable `source_id`;
- `title`, optional `author`, and `edition_or_date`;
- `uri` and supported `source_type`;
- distinct `role` and selection `reason`;
- intended `coverage`;
- authority, recency, difficulty, and overlap notes when known;
- `reputation_basis`, stating why the source is established independently of its availability;
- `access_strategy`, including lawful routes checked or still available;
- `preferred_artifact`, identifying the desired edition or form rather than whichever file was easiest to find;
- `access_status`, `license_status`, and `inspection_status`.

Unknown values must remain explicitly unknown. Do not invent bibliographic, access, or licensing facts.

A candidate may remain in the proposal when access is unresolved. Label it `preferred but unresolved`, record the next lawful acquisition route, and identify any fallback plus the pedagogical compromise it introduces. Never describe a fallback as equivalent without evidence.

Supported deterministic source types are `pdf`, `web`/`html`, `markdown`, `text`, `transcript`, and `repository`. Pin repository proposals to a tag or branch fragment when a reproducible release exists (for example, `https://example/repo.git#v1.2`).

## Course plan

Include:

- observable `outcome` appropriate to the learning-intent mode;
- `assumed_prerequisites` and unresolved placement uncertainty;
- selected `concepts` and why they are high leverage;
- dependency-aware `lesson_order`;
- intentionally `deferred` material and when it becomes relevant;
- expected conceptual and practical assessment work;
- the assessment `pass_standard` when it differs from the default 33% overall and 33% per required concept;
- evidence gaps that may require more source research.

## Canonical chapter

Write a polished concept chapter, not a transcript. Preserve useful earlier material while integrating the current lesson's additions and corrections. Normally include:

- orientation and mental model;
- mechanism or causal structure;
- what transfers to other situations;
- bounded analogies and concrete examples;
- tradeoffs, failure modes, and boundaries;
- related concepts with clear distinctions;
- claim-level source evidence;
- compact lesson/update history.

The deterministic layer expects the full current chapter body for each concept being updated. It records source evidence and update metadata separately.

## Citation

Each citation needs a quality-approved `source_id` and stable `location`. The deterministic layer attaches the current source hash. Include a short `excerpt` only when it materially improves later auditing. Never copy large copyrighted passages.

## Assessment question and result

Assessment records are independently addressable by `assessment_id`. Multiple lesson assessments may simultaneously be `pending` or `in_progress`; generating or freezing one packet never requires another to be completed, passed, paused, or abandoned. Store a separate delivery checkpoint for each open assessment, including the pending question and selected probe when applicable. An optional subject-level selected-assessment pointer is navigation only and must never determine the mutation target implicitly when multiple assessments are open. All question, result, checkpoint, and finalization writes must name the intended assessment. Switching the selected assessment preserves every other record unchanged and does not create a new attempt.

Before delivering question one of a lesson assessment, add every prepared primary question to the assessment record. Maintain a coverage blueprint that maps every substantively taught concept to all applicable reasoning dimensions and to one or more prepared primary questions. Each question record contains:

- exact prompt;
- canonical concepts tested;
- reasoning dimensions tested;
- an explicit rubric written before scoring;
- a non-empty `source_grounding` object for the primary question and its prepared probes.

`source_grounding` contains a short `grounding_note` explaining which factual premises, mechanisms, constraints, boundaries, or task structure the sources contribute, plus a non-empty `sources` list. A source entry is either:

- a course source with `kind: course`, approved processed `source_id`, exact `location`, and source hash; or
- an automatically discovered assessment source with `kind: external`, `title`, `uri` or stable local artifact path, exact `location`, `retrieved_at`, and `content_hash` when downloaded, plus author, publisher, or authority notes when known.

Assessment-only external sources do not require another learner approval and do not become approved teaching-corpus sources. Preserve them with the immutable packet for auditability. The tutor may create and score the question itself; the grounding record supports the question's premises and conceptual demand, not a mandatory external answer key. Record prepared probes against the same grounding object or with their own source entries when they rely on different material.

The rubric must allocate available points among the concepts it tests and mark only genuinely indispensable criteria as critical. This makes per-concept pass calculations auditable even when one integrated question tests several concepts.

Use the rubric field as the hidden packet for that primary question. Along with the scoring criteria, include its reference answer model, acceptable alternatives and boundaries, and 2–3 eligible probes with the precise unresolved relationship or transfer evidence each can test. Do not reveal this hidden material before the learner finalizes the relevant answer.

A result contains either the exact learner answer or a stable artifact reference, plus:

- score and maximum score;
- question-specific feedback;
- assistance or hints used;
- timestamp and attempt context.

At finalization, store total score, maximum score, percentage, the predeclared overall and per-concept thresholds, each concept's earned and available points, unassisted generative-evidence status, critical gaps, and `outcome: passed` or `outcome: not_yet_passed`. When not yet passed, store the exact blocking concepts and reasons. The default standard is 33% overall and 33% for every required concept, plus unassisted generative evidence for each required concept and no critical misconception. An approved course plan may predeclare another standard, but it cannot change after the packet is shown. Optional enrichment must be identified before testing and may not silently become a passing requirement.

When a probe is selected, store its exact text and the learner's response with the primary answer, and identify it in the feedback. Record no more than one selected probe for a primary question. Preserve unused prepared probes in the immutable rubric so the one-probe limit and precommitment are auditable. Reordering unasked questions does not change the packet. Do not add or replace primary questions after delivery begins.

Preserve learner-initiated clarification exchanges with the active question's evidence. Distinguish neutral clarification of wording, supplied facts, or mechanics from substantive assistance that reveals a concept, relationship, hint, or solution. A clarification does not create a new assessment attempt or alter the fixed packet. After answering it, keep the same question pending or continue to the next recorded question according to the existing checkpoint.

Artifact references should include a path and content hash or commit when practical. Do not store secrets, credentials, or unrelated repository content.

For a submitted practical artifact, preserve the submitted snapshot or stable path and hash before evaluation. Record observed executions or test results, the rubric-based score, what worked, every material missing or incorrect part, and any assistance. This result belongs to the submitted state even if the learner later changes the file. Never delay or omit the result while waiting for a correction; store later corrected work as a new append-only attempt.

## Final-exam packet and result

Before delivering question one, store the complete cumulative blueprint and add every prepared source-grounded primary question to the final-exam record. The blueprint maps every substantively taught course concept and every applicable reasoning dimension to one or more primary questions, including several meaningful cross-lesson relationships. Apply the same `source_grounding` schema and keep automatically discovered assessment sources separate from the teaching corpus.

For each primary question, store its exact prompt, concepts, dimensions, and rubric before delivery. Use the structured rubric as the hidden packet for its scoring criteria, reference answer model, acceptable alternatives and boundaries, and 2–3 eligible probes with the precise evidence each can test. Do not reveal hidden packet material before the learner finalizes the relevant answer.

When a probe is selected, store its exact text and the learner's response with the primary answer, and identify it in the feedback. Record no more than one selected probe for a primary question. Preserve unused prepared probes in the immutable rubric so the one-probe limit and precommitment are auditable. Reordering unasked questions does not change the packet. Do not add or replace primary questions after delivery begins.

## Progress judgment

Every assessed concept requires a status and concrete evidence. Valid states are:

- `exposed`: taught but not yet demonstrated;
- `developing`: performance below the concept pass floor, assisted-only evidence, or a critical gap, with the precise deficiency recorded;
- `demonstrated`: the concept passes its working-knowledge standard through adequate independent evidence; full marks are not required, and minor errors or noncritical omissions remain feedback;
- `retained`: demonstrated again after meaningful delay or later use.

Do not derive these states from one undifferentiated assessment average. Use the preallocated per-concept rubric points plus recorded question-level evidence. Under the default standard, a required concept is `demonstrated` at 33% or above only when it also has unassisted generative evidence and no critical misconception. Store the score and qualitative evidence together.

A passed lesson is a durable prerequisite signal, not a claim of perfection. Later lessons and courses should assume its required `demonstrated` or `retained` concepts are known, while preserving noncritical gaps for targeted feedback or natural later use. Do not automatically reopen, reteach, or reassess a passed concept solely because its score was below 100%.

## Learner-memory proposal

The personal profile is one user-level current model shared by all workspaces,
skills, subjects, and tracks through `personal-context`. Subject mastery and
detailed attempts stay in subject progress and assessment records. The profile
stores only durable facts that should change future work, such as stable
background, explanation preferences, useful familiar domains, pacing
constraints, assessment preferences, or analogies that repeatedly helped or
failed.

### Mandatory post-assessment review

Do not decide the lesson's profile changes before its assessment. At lesson completion, create only the pending memory-proposal record required by the deterministic workflow. After the assessment has been finalized, perform an explicit review using all of the following:

- the substantive lesson and learner follow-up questions;
- practical exercise interactions or submitted artifacts, when present;
- exact assessment answers, assistance, feedback, and per-concept judgments;
- the relevant current facts from `personal-context`, so existing keys are updated rather than duplicated.

Ask whether the evidence supports a durable, cross-subject fact that would materially change future teaching. Consider stable background, teaching format, explanation and pacing preferences, assessment preferences, familiar domains, recurring misconceptions about how to approach learning, or analogies and methods that repeatedly helped or failed. Keep subject mastery, scores, temporary confusion, one-off performance, sensitive information, and facts that would not affect future teaching out of the global profile.

The review must produce one visible outcome and may never be blank:

1. **Changes proposed:** show each exact keyed addition or before/after update, its confidence, and concrete lesson/assessment evidence. Wait for explicit learner approval of the exact wording before writing it.
2. **No changes proposed:** say explicitly that the review found no durable global personal-profile change and give a brief reason. Resolve the pending proposal as reviewed with no facts; do not modify the profile.

When the learner explicitly corrects the teaching approach during a lesson, treat that as strong candidate evidence, but still wait until the post-assessment review to present the lesson's profile proposal. Each proposal needs:

- a stable semantic `key` reused when the same preference evolves;
- the proposed current `fact` text;
- confidence and concrete evidence;
- whether it adds a new key or updates an existing one;
- the existing value when proposing an update.

Show the exact add, deletion, or before/after update to the learner and obtain
explicit approval before applying it through `personal-context`. Approval
updates the canonical fact for that key instead of appending a duplicate.
Preserve the approved change, its prior value, source workspace, subject,
lesson, and timestamp in global profile history. Read only relevant current
facts before planning and teaching; do not treat historical, pending, rejected,
or no-change review records as current facts.

Do not globally store temporary emotions, sensitive personal data, or subject mastery that belongs in subject progress. Do not infer a stable preference from one ambiguous response. A direct learner statement about how they want to be taught is sufficient evidence for a proposal, but still requires confirmation of the exact stored wording.
