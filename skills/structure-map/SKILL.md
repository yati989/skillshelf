---
name: structure-map
description: Build a memorable conceptual map of a code library's main parts, core abstractions, relationships, and everyday entry points. Use when the user explicitly invokes the skill to understand a library such as scikit-learn without starting a lesson, course, or test.
---

# Structure Map

Help the user form a durable map of a code library so they know what exists, how the pieces fit, and where to reach for common work.

## Build the library map

- Ground the map in the library version and in material available from the user, the installed package, its repository, or its official documentation. Say when the version or evidence is uncertain.
- Begin with one plain sentence describing the library's job and the boundary of what it handles.
- Group the library into the smallest useful set of major areas, usually three to seven. Show them as a simple tree rather than a flat inventory of modules or APIs.
- Identify the core abstractions or data types that connect those areas.
- Show the normal path through the library as `user inputs/configuration -> core objects or operations -> outputs`.
- Distinguish the stable public API from lower-level implementation details and optional subsystems.
- Explain important relationships: which part creates, consumes, configures, wraps, or extends another part.

## Make the map practical

- Prioritize the 80/20 structure that explains most everyday use. Keep exhaustive API coverage and deep internals optional.
- For each major area, give a concrete cue in the form `When you need X, reach for Y`.
- Use one small example only when it clarifies how parts connect; do not turn the example into a tutorial.
- Include boundaries and commonly confused neighboring parts when that prevents a wrong mental model.
- When the user asks follow-up questions, answer directly and place the answer back into the existing map: where it belongs, what it connects to, and when it matters. Repeat only the affected branch, not the whole map.

## Interaction boundary

This is an open-ended reference conversation, not a lesson or assessment. Do not create a syllabus, learning sequence, quiz, test, homework, recall prompt, progress score, or mastery claim unless the user separately asks for one. Let the user ask as many questions as they want without steering them through predetermined stages.
