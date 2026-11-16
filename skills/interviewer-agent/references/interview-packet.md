# Concept-first interview packet

Build the complete private packet before asking the first question. The packet
contains six to eight broad conceptual themes, normally seven. It is the stable
conceptual answer key and probe plan for the round.

## Packet header

Record:

- target role, category, seniority, job, resume, project, and topic constraints;
- sources used, including job ID, resume claims, and bank entry IDs or URLs;
- the selected themes and why each matters to the target;
- any user-requested difficulty, duration, exclusions, or emphasis;
- whether a quantitative probe is actually justified.

For a broad ML engineering round, choose materially different themes across the
learning system: model behavior, data and evidence, implementation, production,
and engineering tradeoffs. Do not split one family such as precision, recall,
thresholds, and imbalance into four nominally different themes.

## Theme card

Create one complete card per theme:

```markdown
## Theme 1 — <concept family>

- Grounding: <job requirement, resume claim, bank source/theme, or extension>
- Why it matters: <connection to the target>
- Conceptual opening: <exact candidate-facing question>
- Reference model: <short explanation of the underlying mechanism>
- Concept nodes: <essential ideas>
- Required relationships: <cause, constraint, contrast, or implication>
- Important boundaries: <where the model stops applying>
- Acceptable alternatives: <other valid models or explanations>
- Material misconceptions: <errors that change predictions or decisions>
- Specific probe A: <prepared transfer/application question>
- Probe A solution: <answer and conceptual connection>
- Specific probe B: <alternative probe for a different observed gap>
- Probe B solution: <answer and conceptual connection>
- Optional probe C: <only when a genuinely different branch is useful>
- Evidence status: unasked
- Candidate evidence: <fill during interview>
- Assessment gap: <fill during interview>
```

The reference model should express a compact causal structure, not a list of
terms. State what changes, why it changes, what observable result follows, and
which assumptions are required.

## Conceptual opening test

A conceptual question can be broad in importance while remaining narrow enough
to assess. It should identify the relationship the candidate must explain.

Too vague:

> Tell me about overfitting.

Concept-first:

> Why can a model achieve very low training error yet perform poorly on unseen
> data? Explain the mechanism, then name one intervention and the observable
> change that would support your diagnosis.

Too test-like:

> Given these four error percentages, classify two models and calculate the
> improvement.

The opening question should reveal the candidate’s mental model without making
arithmetic the task. Use a later probe to introduce a concrete observation or
changed assumption after the candidate has explained the concept.

## Specific-probe design

Every probe must reuse the opening concept. It may ask the candidate to:

- predict what changes when one assumption changes;
- explain a short execution or data-flow trace;
- choose between two approaches and connect the choice to constraints;
- identify a failure mechanism in a small scenario;
- apply the concept to one exact resume or project claim;
- describe evidence that would distinguish two hypotheses.

Prepare two or three probes so the interviewer can select one that fits the
answer. Ask at most one. Do not ask a second probe to repair a failed first
probe, and do not retest a solution that has just been revealed.

Numerical work is not a default probe type. If a quantitative probe is justified
by the target, keep it short and make the interpretation more important than the
calculation. Use no more than one quantitative probe in a normal round.

## Conceptual comparison

Evaluate each theme as a small concept graph:

1. Extract the candidate’s substantive claims.
2. Map them to the reference nodes or valid alternatives.
3. Check whether the required causal or conditional relationships are present.
4. Use one specific probe only when it adds evidence about transfer or resolves
   the most important ambiguity.
5. Record demonstrated, partial, incorrect, assisted, or unassessed.

Keyword overlap is weak evidence. Conversely, different vocabulary can show the
same correct model. Look for whether the candidate can use the concept to predict
behavior, justify a decision, or explain a failure.

## Packet review

Before the interview:

- confirm there are six to eight non-overlapping themes;
- ensure every opening is conceptual, focused, and free of unnecessary numbers;
- ensure every probe narrows the same concept instead of starting a new topic;
- confirm every solution explains the mechanism and its boundaries;
- remove trivia, puzzle questions, and formula-recall prompts;
- ensure the whole round contains no numerical question by default and at most
  one when the supplied target genuinely warrants it;
- verify the planned sequence moves on after one probe per theme.
