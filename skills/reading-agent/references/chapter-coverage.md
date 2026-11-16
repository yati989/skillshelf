# Complete chapter reading

Use this process for a chapter, lesson, or substantial supplied section. The
goal is a faithful explanation of all substantive material in the requested
scope, not a highlight summary or a sentence-by-sentence paraphrase. Give the
core ideas more explanatory space without dropping the supporting sections.
A general 80/20 preference does not override a request for full chapter coverage.

## Prepare and inspect the complete unit

1. Identify the supplied work, edition/version, and exact requested boundaries.
   Check the text itself: a study guide, synopsis, preview, or incomplete upload
   must not be presented as the original or complete chapter. If boundaries are
   unclear, inspect the contents and neighboring heading before asking the reader.
2. Prepare or reuse Markdown using [workspace.md](workspace.md). Preserve source
   identity and locations. For an existing Markdown file, preparation may simply
   mean verifying and indexing it; do not rewrite the author's wording. For pasted
   text, distinguish user-supplied labels from independently verified publication
   metadata. Use temporary preparation when the reader declines durable saving.
3. Read the entire requested unit in contiguous, bounded portions, tracking the
   ranges inspected. Check each tool response for truncation. Re-read an unfinished
   range in smaller pieces rather than jumping ahead after a truncated response.
   Search locates a passage; it does not replace reading the surrounding material.
4. Check the beginning, transitions, and ending against the original, especially
   when generated chapter files disagree with printed headings or page order.
   Check figures, tables, captions, boxes, footnotes, and relevant endnotes that
   contribute meaning. Inspect the original PDF where Markdown loses their content
   or reading order. A chapter Markdown file alone does not prove a clean extraction.
5. Record missing/unreadable spans and extraction uncertainty explicitly. Repair
   the supplied material where possible; if content remains unavailable, identify
   the missing scope and request it. Explain verified material only as partial,
   with the gap retained. Do not invent text or seek substitute readings.

Finish inspection of the complete available unit before designing its definitive
part map and beginning the chapter explanation. For a requested batch, inspect
the batch before claiming its overall structure. If it cannot be fully inspected,
state the actual inspected scope and leave the overall map provisional.

## Build a coverage map, then choose parts

Maintain a compact working table linking the source to the explanation:

| Source section or span | Substantive content to explain | Part | Inspection | Explanation |
| --- | --- | --- | --- | --- |
| Exact heading plus block/line/page locator | Claims, reasoning, examples, qualifications, or narrative contribution | Part number and title | Inspected / gap | Pending / partial / explained / explicitly skipped |

The table belongs in the session checkpoint, or in the conversation if saving is
declined. It is working reading state, not a personal-profile record. Use the
existing note body rather than inventing new helper commands or schema fields.

- Start from every section and subsection, including introductions, transitions,
  unheaded passages, and the chapter's conclusion. Split dense sections at real
  conceptual or narrative shifts. Do not rely on headings alone.
- For nonfiction, account for distinct definitions, claims, intermediate argument
  steps, mechanisms, evidence, examples, assumptions, distinctions, exceptions,
  objections, and limitations wherever present. For fiction, preserve scenes,
  event order, character changes, voice, imagery, and unresolved ambiguity as
  relevant. Use the genre guidance in `reading-and-memory.md`.
- Account for all source spans. Repeated statements can be grouped and navigation
  artifacts omitted with a short reason; a unique qualification or example cannot
  disappear under a broad section label. Include meaningful side material from
  the extraction check. If a source contains exercises, explain any new concept
  they introduce without assigning or grading them.
- Map every substantive item to a part. Group related material into manageable
  explanations, preserving the author's argument or chronology. Choose the count
  from length and density: five is an example, not a minimum, maximum, or template.
  A short unit may need one part. A long chapter may need many.

## Explain through a visible part map

Begin with the chapter title and central question, then a compact **Chapter parts**
index in explanation order. Give each part a meaningful one-line label and mark
the current part. Start Part 1 in the same response when reading has been requested;
the map does not introduce a separate approval step.

Default to one coherent part per response, with room for follow-up discussion.
Honor a request for several parts or the whole chapter together when feasible;
do not compress away content to fit one response. State any remaining parts.

For the current part, explain what each mapped item says, how its reasoning or
events unfold, and why it matters to the chapter. Develop the author's examples
and the author's own qualifications instead of replacing them with a generic synopsis
or surrounding them with unsolicited caveats. Follow the author-centered style in
SKILL.md: coverage means conveying the author's ideas and details, not auditing them.
Explain
technical ideas concretely before formal notation where helpful; preserve what
the formal statement adds. Label generated analogies and interpretations, and
do not force narrative material into a technical lesson template.

A heading in the index, a passing mention, or a source read by the agent is not
an explanation. Mark an item explained only after its substantive contribution
has actually been communicated. Keep unresolved questions separate from coverage:
an explanation is not proof of the reader's understanding, agreement, or mastery.

At a part boundary:

- Tie the part back to the chapter's central thread, with a brief synthesis.
- Give **Sources used for this part**, using the actually used source locations.
  Label generated examples separately; a pure recap may refer to earlier parts
  and state that it introduces no new source material.
- Show the current progress and next part. Do not append an automatic quiz,
  exercise, or comprehension check. While parts remain, continue when the reader
  asks and do not demand `Done` between parts; ordinary follow-up questions stay
  with the active part. At the final part, apply the chapter closure gate below.

After a detour, answer the question, then restore the current part and next
pending item. If the map needs revision, briefly show the change and retain all
still-pending coverage. Do not silently drop material to fit the original count.

## Check coverage before chapter synthesis

Reconcile the explanation against the complete source inventory, not just the
part titles. Inspect the original spans again where coverage is uncertain.
Explain missed items before calling the chapter fully covered, unless the reader
has chosen to stop or narrow the scope. Report unavailable or explicitly skipped
material honestly. A highlights-only request is a scoped overview, not exhaustive
chapter coverage.

Once coverage is reconciled, connect the parts into a coherent account of the
chapter's argument or narrative, preserve the author's important qualifications and
unresolved tensions in the text, and give **Sources used for this chapter**. Do not
add a separate critical review unless the reader requests it. State briefly whether the
requested scope was fully explained or what remains. This synthesis is not an
assessment and does not start the next chapter or close the reader's questions.

After the final synthesis and lesson summary, mark the chapter **fully explained;
awaiting Done** and explicitly ask the reader to send standalone `Done` when ready
to close it and run the Global Personal Profile review. `next`, `continue`, a saved
checkpoint, or a request for another chapter cannot clear this gate. If the reader
tries to advance before `Done`, briefly remind them and stay with this chapter.
After standalone `Done`, finish and record the review outcome before offering the
next chapter; wait for a subsequent request to start it. Profile changes require
separate exact-wording approval even after `Done`. Follow SKILL.md's chapter
closure gate and the existing personal-context workflow.

When all parts of a lesson or chapter have been explained, finish its synthesis with
an **Lesson summary**: a concise set of bullet points capturing the author's central
ideas and the important supporting distinctions, examples, or qualifications. Keep it
faithful to the source and consistent with the coverage map. If the reader stops early
or material remains unavailable or unexplained, label the summary partial and include
only what was covered; do not imply the lesson is complete.

When the entire book has been read, finish with a **Book summary by lesson** that
combines the lesson summaries already produced, in reading order, under each lesson's
title. Carry those bullets forward as the book-level recap; do not ask the reader to
restate them or create a replacement summary that loses the lesson-by-lesson record.
Include only completed lessons, and label any partial lesson and its remaining scope.
Do not produce this book-level recap just because one chapter was completed.

At a meaningful pause or resumption checkpoint, preserve:

- Source ID/version, requested chapter and boundaries, Markdown path, and locators.
- The coverage table and part index, including what was inspected versus explained.
- Extraction gaps, partial explanations, explicit reader skips, and open questions.
- Reader closure status (`awaiting Done` or closed), profile-review status, and
  the exact next part and source span. Before `Done`, another chapter is a candidate
  next unit, not an authorized transition; keep fully explained coverage distinct
  from reader closure. Preserve this gate on resumption.
- The completed lesson summary bullets, saved under the lesson title in the book's
  session note, and which lessons remain. Preserve the bullets so the final book
  summary can carry them forward across sessions.
- The combined **Book summary by lesson**, saved in that session note when the
  whole book is complete.

Resume from the next pending item after checking the source version. If it changed,
reconcile affected ranges before carrying forward their coverage. An old checkpoint
that merely says “Chapter 1 discussed” does not prove every section was covered;
recover evidence where available and label uncertain coverage rather than inventing it.
Standalone `Done` closes the current discussion and triggers the existing profile
review, even if coverage is partial. Record what remains and present the review
outcome; do not force more teaching or relabel unfinished material as complete.
Only after that closure and review may a subsequent request start another chapter.
