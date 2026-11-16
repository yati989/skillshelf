# Workflow and gates

Use this reference when starting or resuming a subject-learning workflow.

## New subject

1. Identify the subject, learning intent, and first track name.
2. Initialize the subject with `kb-tutor init`.
3. Build a reputation-first candidate map for the useful source categories and roles; do not pre-filter it to easy or official downloads.
4. For each preferred candidate, pursue and verify lawful acquisition routes, recording attempts, unresolved access, and any quality tradeoff in a fallback.
5. Select a minimum viable complementary set and prepare the complete source records described in `records.md`.
6. Present the proposal without acquiring sources.
7. Record an explicit approve or reject decision for every source.
8. If the set is inadequate, revise the proposal through another research pass.
9. Obtain final corpus approval.
10. Run source processing and inspect the quality report and warnings.
11. Resolve critical failures before treating the corpus as ready.
12. Run placement, propose the course plan, and obtain plan approval.

## Quality-first source discovery

For each relevant category—normally foundational books, surveys or papers, standards or primary documentation, practical material, and current evidence where needed—use two distinct passes:

1. **Reputation pass:** identify the sources experts would choose if access were irrelevant. Record why each is respected and what unique role it could play.
2. **Access-resolution pass:** search for the exact work and edition through lawful channels. Prefer an author-posted manuscript, institutional repository, legitimate open edition, official release, library copy, or learner-supplied owned copy. Confirm provenance, completeness, edition, and license before marking it accessible.

Do not let availability rank candidates during the reputation pass. Do not let reputation erase acquisition constraints during the access pass. If the best source remains inaccessible, show it as unresolved, explain what was tried, and distinguish a temporary fallback from an equivalent substitute.

## Core state sequence

```text
source_research
  -> source_review
  -> corpus_approved
  -> source_quality_review (when extraction needs human review)
  -> sources_ready
  -> course_review
  -> course_approved
  -> exploring
  -> assessment_pending
  -> assessing
  -> track_ready
```

These phases describe the currently selected workflow focus, not a global exclusivity rule for lesson-assessment records. Multiple lessons may have independently prepared `pending` or `in_progress` assessments. A standalone `Done` for another explored lesson may curate that lesson and generate its frozen packet without requiring an existing assessment to be completed, passed, paused, or discarded. Address assessment mutations by assessment ID, preserve each delivery checkpoint, and change the selected delivery focus without changing other packets. If the deterministic layer cannot address multiple open assessments safely, extend or repair it rather than blocking the learner or reusing a global pointer. The requirement that all non-deferred assessments be complete applies at the course-final-exam gate, not at assessment-generation time.

Do not skip approval gates by manually editing the state file. When a command refuses a transition, inspect the current status and resolve the missing decision.

## Source changes

- A rejected source may be replaced during source review.
- A failed conversion returns the corpus to preparation; do not teach from the failed derivative.
- A new source version is a new immutable source artifact. Mark dependent retrieval chunks, concept mappings, and chapter claims for revalidation.
- A conversion with warnings or low-confidence blocks remains unavailable until its quality report is explicitly approved.
- For time-sensitive tracks, check evidence freshness before planning or resuming lessons. Present additions or replacements through the same approval flow.

## Lesson lifecycle

1. Begin a lesson with its intended canonical concepts.
2. Classify whether the lesson is programming-suited practical or theoretical/non-programming. For a programming-suited practical lesson, plan a concept-linked programming exercise as the final lesson part.
3. Before the first explanation, present the mandatory short **Lesson parts** index in teaching order and mark the starting part; include **Practical programming exercise** last when applicable.
4. Keep explanations and follow-ups in conversation while the state is `exploring`. At the end of each completed lesson part, show its compact **Sources used for this part** block with only the retrieved sources and precise locations actually used, or explicitly state that it adds no new source material and identify the earlier sourced part it applies.
5. For a programming-suited practical lesson, present and scaffold the programming exercise before treating the lesson as ready to close, unless the learner explicitly declines or postpones it.
6. After the final lesson part and its source trail, give a concise **Lesson summary** in bullet points with bolded key takeaways. Remain in the current lesson for follow-ups until the learner gives an explicit standalone `Done`. Only that signal opens the write-and-assess gate and permits moving to the next lesson. `Next` or `continue` advances within this lesson only; after the final part, it must not start another lesson or an assessment.
7. Prepare full replacement text for every canonical chapter being updated plus its exact citations.
8. Complete the lesson once; this writes chapters, a pending assessment, and an empty pending memory-proposal record. Do not decide profile changes yet. Do this even if another lesson assessment remains pending or in progress; preserve both records independently.
9. Autonomously source real assessment material from the existing corpus and, when useful, external web or downloadable sources without another approval round. Prepare and persist the complete fixed packet and coverage blueprint, storing source grounding for every primary question and prepared probe alongside per-concept rubric points, critical criteria, and the predeclared pass standard. Keep external assessment sources separate from the approved teaching corpus. The learner may generate packets for other completed lessons or switch the selected delivery focus without closing this one.
10. When this assessment is selected for delivery, ask each primary question with at most one prepared probe and record its result against this assessment ID.
11. Finalize only when every recorded question has a result and every concept has an evidence-based judgment. Store total and per-concept scores plus `passed` or `not_yet_passed`. By default, passing requires at least 33% overall, at least 33% on every required concept, unassisted generative evidence for each required concept, and no critical misconception; it never requires full marks.
12. As the final lesson step, read the lesson, follow-ups, practical interactions, finalized assessment evidence, and relevant current facts from `personal-context`; perform the mandatory profile review.
13. Show either exact keyed proposals with evidence and confidence or an explicit no-change result with a brief reason. Never leave the review blank or pending merely because no proposal was obvious.
14. Apply only explicitly approved additions, updates, or deletions through `personal-context`, preserving each change in global profile history. If there is no proposal, resolve the pending record with no facts and do not mutate the profile.

Only after step 14 is the lesson's post-assessment lifecycle fully closed. A pending profile proposal remains approval-gated but does not block the final-exam transition; leave it pending if the learner proceeds without approving it. For remediation or later retention, create a separate reassessment attempt; never reopen or overwrite the completed assessment.

When a lesson passes, later lessons and courses treat its required `demonstrated` or `retained` concepts as established prerequisites and do not automatically reteach them. Preserve noncritical weaknesses as feedback. Revisit only on learner request, a planned retention check, or fresh evidence that a dependency has failed. When a lesson is `not_yet_passed`, it may still close, but its blocking concepts cannot be silently assumed downstream.

If the learner asks a question during assessment, clarify it and continue the same selected assessment from its pending primary question or next recorded checkpoint. If the learner explicitly switches to another lesson assessment, preserve this checkpoint and select the requested packet without creating a new attempt. Do not return the lesson to exploration, require a fresh `Done`, revise the packet, or create a reassessment merely because delivery focus changed. Record substantive hints or revealed assessed relationships as assistance; neutral wording and task-mechanics clarification do not count as the tutor's optional probe.

## Course completion and final exam

After finalizing the final planned lesson assessment, check the saved records for every non-deferred lesson and its assessment, report any incomplete items, and tell the learner: **Say `Done` to begin the final exam.** Give the assessment results and mandatory profile-review outcome, but do not make gap discussion, remedial teaching, reassessment, or profile-proposal approval a prerequisite.

At this post-assessment checkpoint, a standalone `Done` means **check readiness and start the final exam**. Recheck the latest approved course plan and saved completion records, including when resuming in a new chat. If every non-deferred lesson and its assessment is complete, proceed directly through the exam preparation below and show question one after announcing the fixed count; do not ask another readiness question. Completion is distinct from passing: a finalized `not_yet_passed` assessment counts as completed. If any required lesson or assessment is incomplete, name its exact identifier and status and keep its existing packet/checkpoint; do not silently skip it or restart a completed assessment. When the remaining item is completed, offer the same `Done` transition again.

Interpret `Done` according to the current phase: during lesson exploration it opens that lesson's assessment; while an assessment has unanswered questions it does not complete or restart the packet; after the final lesson assessment it triggers the readiness check above. If a cumulative final exam already exists and is unfinished, resume its saved checkpoint rather than creating a duplicate. A completed final exam is not restarted by `Done`; a new attempt requires an explicit reassessment request.

Once that post-assessment `Done` confirms every non-deferred lesson and its assessment is complete:

1. Read the approved plan, canonical chapters, progress judgments, and prior assessment prompts and results.
2. Build a cumulative exam blueprint that covers every substantively taught concept and every applicable reasoning dimension, then autonomously find real source material capable of grounding difficult questions for every required evidence route.
3. Create a distinct append-only final-exam record under the active track, then add the complete fixed packet of source-grounded primary questions, grounding records, prepared probes, and hidden rubrics before delivering question one; do not reuse a lesson assessment or overwrite earlier evidence. Assessment-only sources require no additional approval and do not alter the teaching corpus.
4. Announce the primary-question count, deliver questions one at a time, and allow at most one prepared probe per primary question. After that answer and optional probe, record the evidence and move on; do not add rescue questions or probe until the learner succeeds.
5. Record exact responses, assistance, total and per-concept scores, feedback, judgments, and the explicit exam outcome. Unless the approved plan predeclared another standard, `passed` requires at least 33% overall, at least 33% on every required concept, unassisted generative evidence for each required concept, and no critical misconception. Full marks are not required. Use `retained` only when the timing and evidence satisfy the normal delayed-reassessment rule.
6. Remediate precise gaps through new teaching and append-only attempts.
7. Declare the course passed only after the completed final exam meets its pass standard. If the learner postpones, declines, or does not yet pass it, report the exact pending or `not_yet_passed` state rather than claiming course completion. A passed course makes its required demonstrated concepts available as assumed prerequisites for later courses.

If the deterministic workspace cannot represent a separate cumulative final exam faithfully, extend or repair that layer before claiming the final exam has been persisted. Do not substitute ad hoc chat-only state.

## Recovery

All deterministic writes are atomic. After interruption, inspect the subject state and durable manifests rather than assuming the last command completed. Re-run only idempotent preparation steps or explicitly create a new assessment attempt; never overwrite recorded answers.
