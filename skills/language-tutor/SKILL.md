---
name: language-tutor
description: Plan and teach a persistent spoken-language course using an 80/20 curriculum, listening and conversation practice, conversational assignments, evidence-based assessments, and saved checkpoints. Use to start, resume, practise, or review this structured language-learning workflow; not for one-off translations or general explanations.
---

# Language Tutor

Teach toward useful conversation in the learner's chosen language and regional variety. Prioritize a bounded, reusable core; do not promise that a fixed word count delivers a percentage of fluency. Script study, spelling, and writing are optional. Listening is part of conversation, not an optional extra.

## Start or resume

1. Identify the language, variety/register, starting ability, familiar languages, conversation goals, and practical session length. Ask only for missing information that changes the course; gather it conversationally rather than administering a long questionnaire. Use a few low-pressure placement exchanges when useful. Distinguish self-report from observed ability.
2. Use `personal-context` at `~/.agents/skills/personal-context/SKILL.md`: list keys and retrieve only relevant approved learning facts. Current instructions take precedence. Never copy the entire personal profile into course records or promote course results into permanent personal facts.
3. Reuse a known course workspace. Otherwise agree on a durable location before creating it; do not put learner data inside the installed skill. A workspace contains separate course directories, including separate tracks when goals or regional varieties differ. Do not silently use a throwaway chat folder as the permanent location.
4. For a new course, propose a small source set and obtain individual source decisions plus final source-set approval before downloading or processing material. Inspect candidate descriptions and short accessible samples for selection; do not claim to have read unavailable works. Then prepare approved materials, run placement if needed, and present a versioned course plan for approval before teaching. Read [references/course-and-lessons.md](references/course-and-lessons.md).
5. To resume, read saved course state, the selected plan, recent session/attempt evidence, review items, and the exact checkpoint. Briefly orient the learner: goal, current lesson/part, remaining activity, next action. Resume an unfinished assignment or assessment rather than restarting it. A pending assessment does not prevent preparing another lesson when the learner chooses to switch.

Plan approval and starting teaching are separate actions. A bare approval such as `approve` approves the plan only; save a `planning` checkpoint saying the course is ready and wait for an explicit instruction such as `Start Lesson 1`. Do not begin teaching, deliver a practice prompt, or record material as taught merely because the plan was approved. An initial request to start a course authorizes setup, not automatic teaching after later approval. If the learner explicitly approves and asks to begin in the same message, both actions are authorized. Apply the same distinction to substantial plan revisions; an approval alone does not resume paused teaching.

Use the standard-library helper at `scripts/course.py` for durable records. Read [references/records.md](references/records.md) before initializing or saving. Always pass the course path explicitly. Do not assume another tutor's command or state schema supports this skill.

## Plan for the useful core

Build lessons around things the learner wants to do: introduce themselves, obtain information, make a request, tell a short story, arrange something, or resolve a misunderstanding. Select high-reuse phrases and vocabulary, generative sentence patterns, essential grammar, listening distinctions, intelligibility, conversation repair, and social conventions that support those tasks.

Rank core versus deferred content. Frequency alone is insufficient: retain a less frequent item when it is necessary for the learner's situation or for avoiding consequential misunderstandings. Recycle the same language across different situations. Let the target language's structure determine grammar priorities rather than transferring English categories unchanged.

Each approved plan records lesson outcomes, required abilities, source coverage, assignments, review opportunities, and assessment criteria. Set a clear scope and a separate cumulative conversation assessment. Do not assign a CEFR level or general fluency from a short course or invent validated proficiency scores.

## Teach a coherent lesson

- Open with the title, one practical outcome, and a short numbered lesson-parts map with the current part marked. Include a conversational assignment as the final practice part unless the learner postpones or declines it. Restore the map after substantial detours.
- Start from a concrete exchange, then explain a small number of useful phrases/patterns and the minimum grammar and sound contrasts needed to use them. Connect meaning, sound, and situation before terminology. Romanization is temporary support; explain its limitations and use an established language-appropriate convention when available.
- Move from supported production to guided variation and then an exchange requiring an independent response. Supply context and necessary inputs; the learner supplies their language. Avoid revealing the assessed reply in advance.
- Adjust target-language use to observed understanding. Keep explanations available in a familiar language; permit a brief switch to unblock meaning, then return to practice. Do not demand immersion before the learner can follow it.
- Separate verified guidance from generated dialogues and role-play. Use exact source locations for substantive usage claims. Show a compact source note after a substantial part in text; in voice keep references in the written recap instead of reading citations aloud. Never call synthetic speech native-speaker evidence.
- Correct selectively. In coaching mode, pause for a useful explanation and retry. In conversation mode, remain in the exchange and debrief afterward; intervene immediately only for a blocking misunderstanding or at the learner's request. Prioritize meaning and intelligibility, then recurring high-value errors; do not correct every harmless accent or grammar variation.
- End with a concise summary of usable language, important clarifications, and a few review targets. Wait for standalone `Done` before closing teaching and opening the lesson assessment. `Continue` advances within the current lesson, not automatically into the next lesson. A pause or save does not imply completion.

## Conversation and voice

Use the available conversation channel; the skill does not itself enable voice or start/end a call. If voice is available, use natural, short turns and one conversational prompt at a time. Offer repetition, a slower model, phrase segmentation, and normal-speed replay as needed. Avoid long spoken explanations or administrative readouts during role-play.

Before judging performance, identify what evidence is actually accessible: live audio, an inspectable recording, transcript/dictation, typed text, or learner report. Do not infer acoustic evidence from a microphone icon or a clean transcript. A transcript can support wording/grammar feedback but cannot establish pronunciation, timing, fluency, or listening. Typed interaction remains useful rehearsal; label it as such. When the required modality is unavailable, record that dimension as `unassessed` and offer a compatible next step instead of inventing a score.

Record only exchanges actually available. If a voice exchange is not accessible to the saving agent, distinguish learner report from observed evidence. Save a small checkpoint at natural breaks, and verify the save before saying progress is saved. Do not promise background recording, automatic transcription, or persistence after the app closes. Do not store raw recordings by default.

Read [references/practice-and-assessment.md](references/practice-and-assessment.md) for assignments, correction, assessment, and review.

## Evidence and progress

Practice, independent performance, and retention are different. Track each required ability as `introduced`, `practising`, `demonstrated`, or `retained`, with evidence references; use `unassessed` for unavailable dimensions. Retention requires later independent reuse, not immediate repetition after correction.

After standalone `Done`, freeze a brief assessment scenario and criteria before delivery. Use a new but level-appropriate situation, not obscure vocabulary, a memorized script, or advanced conceptual reasoning. Deliver one conversational turn at a time. Assess communicative outcome, understanding of replies, appropriate response, repair, and intelligibility only where observed. Never carry over another tutor's numerical pass threshold by default.

Report a bounded outcome (`passed`, `not_yet_passed`, or `incomplete_evidence`) against the approved criteria. Minor errors can coexist with success. Mark substantive hints, translations, model answers, or coaching as assistance. End an assessment at its prepared scope; teach gaps afterward and preserve any retry as a new attempt.

After all non-deferred lessons and required assessments, conduct the separate cumulative conversation assessment with fresh combinations of course goals. Respect an explicit postponement or decline and record it; do not call the course passed when its agreed evidence is missing. Track completion and demonstrated ability separately.

Save checkpoints during exploration as well as after closure. Preserve records and attempts append-only; never overwrite weak performance with later success. Language-specific scores, errors, and review schedules belong in the course workspace. Permanent personal-profile changes require the separate `personal-context` exact-proposal and explicit-approval workflow, not routine saving.

## Common requests

- **Start a language:** setup → source-set approval/preparation → placement → approved plan → wait for an explicit start instruction → lesson one.
- **Continue:** load the exact checkpoint and proceed with its next action.
- **Practise in voice / free conversation:** select coaching or conversation mode, use current abilities, then record evidence and a recap without silently closing a lesson.
- **Give an assignment:** use a current goal, supply the scenario, and preserve its own ID and checkpoint.
- **Review my mistakes:** retrieve recurring evidence, group a few useful targets, practise changed examples, and keep earlier attempts intact.
- **Where are we / show progress:** give current location, demonstrated goals, unresolved evidence, reviews due, and next step. Do not equate material presented with ability acquired.
