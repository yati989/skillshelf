# Reading and personal context

## Adapt the reading

Apply the author-centered explanation style in SKILL.md. Use the following approaches to convey the supplied work's own content, not to add routine critique:

- For philosophy, explain the question, motivating problem, argument, assumptions, counterexamples, and competing positions developed in the text. Preserve the author's reasoning before offering evaluation when requested.
- For fiction, attend to voice, scene, imagery, character, structure, and ambiguity. Do not reduce a story to a lesson or diagnose the author or reader from a passage. Mark speculative interpretations as such.
- For religious material, distinguish textual interpretation, tradition-specific views, practice descriptions, historical claims, and empirical assertions. Engagement with a tradition does not identify the reader's faith.
- For science and economics, explain the author's models, assumptions, evidence, examples, and conclusions, including limitations the author discusses. Use natural attribution rather than repeated verification disclaimers or unsolicited methodological criticism. Handle a requested external fact-check or critique separately and identify outside evidence clearly.
- For comparisons, choose the actual shared question and specific passages. Do not treat similar words as proof that authors mean the same thing.

Start with what makes the material intelligible to this reader. Familiar examples can help, but preserve what the analogy leaves out. Discussion may move from a line to its chapter or from an idea to another work; reconnect to the source when a detour has changed the question.

## Personal evidence and the global profile

The approved current model is the global profile managed by `personal-context`.
The reading workspace's `self/` notes are evidence, not another current profile.
Useful evidence areas are context, interest timelines, recurring patterns,
subject familiarity, open questions, and explicitly expressed views. Create an
evidence note only when there is something useful to retain.

Keep three kinds of attribution distinct:

1. `user_statement`: something the reader actually stated. Preserve a quote or faithful paraphrase and the session/date/context. During reading, retain it in the session checkpoint; add or change a permanent global fact only after the standalone `Done` review and the reader's approval of the exact proposal.
2. `historical_observation`: a bounded observation from an already analyzed archive. Preserve the period, method, and material coverage limitations. The original behavior may belong to a shared account or a task for somebody else.
3. `assistant_inference`: an interpretation or candidate connection. Include supporting observations, uncertainty, and what remains unknown. Do not promote it to a user belief through repetition.

Worldview/background/preferences entries attributed to the user require their actual statements. If evidence only supports a hypothesis, file it as such under patterns or hypotheses. Self-reported familiarity and demonstrated discussion behavior also have different evidential strength; neither implies permanent mastery.

When the user corrects something, treat the correction as authoritative in the current conversation and stop relying on the old interpretation. Propose the exact global-profile correction during the standalone `Done` review, or immediately when the user explicitly asks to correct the saved profile; apply it only after approval. For example, "those searches were for someone else" preserves the historical evidence summary while removing its use as a current fact about the reader's interest. If their view changes, preserve the old position in profile history and make the approved replacement current. Do not silently revise an explicit user statement into a more elaborate position.

Use approved global facts with their provenance and uncertainty. Do not copy a
preference into evidence notes or the wiki as another current value. Project
records may support a proposal; only `personal-context` owns the current fact.

## Checkpoints

An effective session checkpoint answers what we read, what became clearer, which interpretations or disagreements remain, what the reader said, and where to resume. Include only fields that have content; no transcript dump or artificial completion ceremony.

For chapter reading, preserve the coverage map from
[chapter-coverage.md](chapter-coverage.md), distinguishing inspected text,
explained material, and pending items. Reader closure and complete source
coverage are separate: a fully explained chapter remains **awaiting Done** until
standalone `Done` closes the discussion and triggers the profile review. An early
`Done` closes the discussion with unfinished items still visible. Record closure
and review status so resuming with `next` cannot bypass a pending chapter gate.
Do not treat a general preference for concise or high-return
learning as permission to silently skip sections in an exhaustive chapter request.

If the reader says "pause here," save the checkpoint unless they declined saving. If they are simply asking the next question, continue reading. If a quick one-off explanation does not produce durable value, no wiki page is needed.

A checkpoint and a profile adaptation are separate. Ordinary pauses, chapter
transitions, and session endings may save progress or evidence, but do not
change the global profile. Only a standalone `Done` triggers the closing profile
review. It is required before starting another chapter in sequential reading;
`next` only advances between parts of an open chapter. At the chapter boundary,
remind the reader to send standalone `Done` rather than silently advancing. Read
the complete substantive unit since the last close, relevant
follow-ups, relevant approved global facts and evidence, and the new checkpoint.
Always report either:

- **Proposed profile changes:** exact additions or before/after updates, each
  with attribution, evidence, scope, and confidence; or
- **No profile change proposed:** a brief reason why the discussion did not
  justify durable adaptation.

Use the `personal-context` interface to record the review and wait for explicit
approval of the exact proposal before changing current facts. Partial approval
applies only to the named keys. Rejection, silence, or approval of the checkpoint
itself leaves the profile unchanged. After an approved write, report the keys
changed; the shared interface retains before/after history.

Before saving an interpretation as a wiki note, make its sources and status visible. A source pointer is necessary for traceability but does not prove semantic support: inspect the cited text. A session-only insight can cite the saved session as a link and identify itself as discussion-derived, rather than inventing a book citation.
