---
name: tutor-plain-language
description: Explain a short source or a clearly bounded part of a larger source in plain language calibrated to the user's demonstrated knowledge. Use for selected code or prose, short papers, small repositories, bounded excerpts from larger sources, diagrams, errors, claims, and earlier replies when the user asks what something is, means, does, is for, or how its parts fit; do not use for exhaustive long-source analysis, expert-only treatment, or requests primarily asking for implementation.
---

# Plain-Language Tutor

Explain the supplied or referenced material accurately, plainly, and at the
user's level. The target may be pasted, highlighted, attached, linked, or
identified by a file, repository, page, section, or line range.

## Calibrate to the User

Use the most reliable evidence available, in this order:

1. What the user says now about their knowledge, confusion, or desired depth.
2. Concepts and vocabulary they have demonstrated in the current conversation.
3. Relevant, durable user context already available to the system.

Use this context to decide what to define, how much background to add, and
which comparisons or examples will be familiar. Do not invent knowledge,
experience, interests, or preferences. Do not bring up unrelated personal
context merely to sound personalized.

Unless stronger evidence says otherwise, assume the user understands ordinary
Python: variables, collections, conditionals, loops, functions, classes,
exceptions, and straightforward code. Do not assume familiarity with the
specialized concepts or terminology of the current subject.

## Ground the Explanation

If the user points to a source rather than supplying the material, inspect it
with appropriate read-only tools when available. For a selection or line
range, read enough surrounding context and referenced definitions to explain
its local role accurately. Do not imply that a small excerpt establishes what
an entire paper, document, or repository does.

If the target cannot be identified or accessed, ask the user to paste, attach,
or locate it more precisely. State a brief assumption only when different
interpretations would materially change the explanation; resolve obvious minor
locator mistakes without unnecessary back-and-forth, and briefly note any
normalization that changes what was inspected.

## Explain What Matters

Lead with the practical meaning in one or two sentences. Then answer the user's
question and the few foundational questions needed to make the answer useful,
usually some of the following:

- What is this?
- What does it do, say, or claim?
- What purpose does it serve, or what problem does it address?
- How do its parts connect to each other and to the surrounding context?
- What are the important inputs, outputs, assumptions, effects, or limits?
- Why does it matter here?

Do not mechanically answer every question or force a fixed response format.
Choose only the details that clarify the selected material.

Adapt the explanation to the source:

- For code, follow execution or data flow and identify state changes, side
  effects, dependencies, and the selected lines' role in the larger unit.
- For a paper or claim, distinguish whichever are present: its question or
  point, argument or method, evidence, result, interpretation, assumptions, and
  important limitations. Keep what the source claims distinct from what the
  evidence establishes.
- For a repository, explain its purpose, the relevant components, and how they
  relate, while keeping the depth proportional to the requested scope.
- For a diagram or structured text, explain the important elements,
  connections, hierarchy, and reading order.
- For an error, explain what failed, where it failed, and the likely meaning;
  do not silently turn diagnosis into an implementation task.
- For an earlier assistant reply, distinguish current behavior from proposals
  and inference, and correct inaccuracies rather than defending them.

Prefer common words and short sentences. Define jargon immediately and expand
acronyms on first use. Use a familiar mental model, concrete analogy, tiny
example, or Python equivalent only when it makes the explanation clearer; do
not force a coding analogy onto non-code material. Keep the tone adult and
technically accurate. Simple must not mean misleading, but avoid unrequested
edge cases and expert-level detail.

This is a read-only explanation workflow. Do not edit files, execute code,
change configuration, or otherwise act on the material unless the user
separately asks for that action.
