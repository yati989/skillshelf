---
name: auto-complete
description: "Turn rough notes, pseudocode, or broken code into a working program."
---

# Auto Complete

Produce the complete working version of the user's intended program, function, or workflow from whatever starting material they provide. Inputs may be comments alone, line-by-line procedural instructions, informal pseudocode, broken code, or any mixture of these.

## Recover intent and implement

- Treat the user's stated requirements and procedural comments as the intended behavior. Use existing code as evidence of intent, but correct it where it contradicts those requirements or contains defects. Resolve material contradictions with one focused question when the intended behavior cannot be inferred.
- Use the programming language the user specifies. Otherwise use the language clearly implied by their code or project. If neither supplies a clear choice, ask which language to use.
- Resolve minor gaps with the simplest reasonable implementation. Ask only when missing information would materially change correctness, inputs, outputs, or scope.
- Deliver the entire requested unit, including necessary imports, definitions, data flow, and entry point where appropriate. Do not stop at a patch, disconnected snippets, TODOs, ellipses, or omitted helper functions.
- Fix syntax, logic, and integration defects, and implement the missing steps. Restructure messy code as needed to make the requested behavior work; preserve useful interfaces and project conventions unless the requirements require a change. Keep unrelated code outside the scope.
- Follow the intended sequence where it affects behavior; express informal instructions idiomatically in the target language. Preserve useful explanatory comments and replace obsolete placeholders or misleading comments.
- Include only dependencies and setup needed for the requested implementation. Use configuration for external credentials or user-specific resources; do not fabricate real credentials, paths, API behavior, or business rules to make code appear complete.

## Verify and deliver

- Check the completed implementation against each requested step and ensure its pieces connect from input to output. When execution is available and appropriate, run a focused syntax or build check and a representative example or relevant existing tests. Avoid running operations with live external effects solely for validation.
- When the input is pasted in chat, return the complete implementation in a language-tagged code block. For multiple files, label each file and provide its complete contents. Include essential dependency or run instructions only when needed to use the result.
- When the user provides files to repair, edit them directly and link the completed files before explaining the code. Mention any material unresolved requirement or verification limitation; claim successful execution only when it was actually observed.
- After delivering the code, explain how it works in plain language: its inputs and outputs, the main steps in execution order, and how the important functions or blocks connect. Explain non-obvious logic, significant fixes to the original code, and assumptions that affect behavior. Scale the detail to the code's complexity; use a small example when it materially clarifies the flow.
- Keep the explanation grounded in the delivered implementation. Avoid mechanically paraphrasing every line, unrelated lessons, alternative implementations, or unrelated improvements unless requested. If the user explicitly requests code only, omit the explanation.
