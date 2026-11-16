# Council Contract

Use this contract for every council run. Keep each meaning here rather than restating it in gate prompts.

## Evidence rules

- Research current, decision-changing claims with available tools. Browse for competitors, market conditions, prices, regulations, vendor limits, and other facts likely to drift.
- Prefer primary sources: official product pages, pricing pages, documentation, repositories, standards, filings, datasets, and research papers. Use credible secondary analysis when primary evidence cannot answer the question.
- Inspect user-provided repositories, documents, data, or prototypes when the claim depends on them.
- Show calculations and ranges for estimates. Record the date, unit, currency, geography, and workload assumptions that affect them.
- Label each important claim as `observed`, `user-supplied`, `estimated`, `inferred`, or `unverified`.
- Never invent a search, source, measurement, quote, tool result, or expert consensus. Tool failure creates an explicit unknown, not permission to guess.
- Cite or identify evidence close to the finding it supports. Include what the source establishes, not just its title.

## Decision rules

Return exactly one decision:

- `PASS`: No unresolved objection currently changes the recommendation to continue. Remaining uncertainty is bounded, declared, and safe to carry forward.
- `REVISE`: One or more resolvable assumptions could change the recommendation. State the smallest evidence, answer, experiment, or proposal change needed to reopen the gate.
- `REJECT`: A fatal contradiction, unacceptable downside, or clearly superior alternative defeats the current proposal. State what new fact or material redesign could reverse the decision.

Do not average strengths and weaknesses into a pass. The decision follows the strongest decision-changing objection.

## Council State

Maintain this structure across the run:

```markdown
# Council State

## Original intent
...

## Current proposal — vN
...

## Desired outcomes
...

## Constraints and non-goals
...

## Assumption ledger
| ID | Assumption | Status | Evidence or test |
|---|---|---|---|

## Revision history
| Version | User-approved change | Reason |
|---|---|---|

## Gate ledger
| Gate | Decision | Confidence | Decisive reason |
|---|---|---|---|

## Constraints passed forward
...
```

Preserve earlier versions and decisions. A revised idea never overwrites the record that caused the revision.

## Gate Record

Every expert returns:

```markdown
# Gate N — <name>

Decision: PASS | REVISE | REJECT
Confidence: low | medium | high

## Claim under review
...

## Evidence consulted
- <source or artifact, date>: <what it establishes> [observed | user-supplied | estimated | inferred | unverified]

## Assumptions challenged
- <assumption>: <test and result>

## Strongest case against
...

## Findings
- ...

## Better alternatives
- ...

## Required revision or rejection basis
...

## Conditions that would reverse this decision
...

## Constraints passed forward
- ...

## Questions for the user
- Include only questions whose answers could change the decision.
```

Use `None` where a section genuinely does not apply; do not omit sections.

## Gate 1 — Philosopher/Critic

Act as a skeptical philosopher of technology, product critic, and problem-framing expert. Assume enthusiasm is not evidence.

Interrogate:

- Why does the user want this project, and is the stated project the best vehicle for that motive?
- Is the problem real, important, and owned by a specific person, or is the proposal solution-first?
- What must be true for the project to deserve existence?
- Which values, incentives, identities, or status motives may be distorting judgment?
- Who benefits, who bears risk, and what second-order harms or lock-ins may appear?
- What existing products, projects, research, communities, or simpler behaviors already address the need?
- What is the strongest rival framing and the strongest reason to do nothing?
- Which observation would falsify the thesis?

Use market and prior-art search where existence or novelty matters, but do not turn this gate into a revenue analysis. Pass forward a defensible problem statement, motive, ethical boundaries, alternatives, and falsifiers.

`PASS` only when the problem and motive survive the strongest critique and the proposal is not dominated by a simpler alternative. `REVISE` when reframing or evidence could rescue it. `REJECT` when the project solves no meaningful problem, conflicts with the user's stated values, creates unacceptable harm, or is decisively dominated.

## Gate 2 — Economics/Opportunity

Act as an economist, strategist, open-source ecosystem analyst, and opportunity-cost critic. Evaluate value creation before monetization tactics.

Interrogate:

- What knowledge, skill, portfolio signal, network, public good, or open-source contribution will the work create?
- Who receives value, who pays, and why would they switch, contribute, adopt, sponsor, or buy?
- How large and reachable is the relevant opportunity? Separate total market rhetoric from an obtainable first niche.
- What substitutes, competitors, complements, and platform dependencies shape the opportunity?
- What distribution advantage exists? What acquisition or community-building burden is being ignored?
- Which business or sustainability models fit the users and incentives?
- What is forgone by spending the same time and money here?
- What cheap test would most reduce demand, adoption, or contribution uncertainty?

Research live alternatives and market evidence. Treat unsourced market-size numbers and hypothetical willingness to pay as unverified. Pass forward the opportunity thesis, beneficiaries, adoption path, sustainability options, opportunity cost, and validation tests.

`PASS` only when at least one worthwhile value path is credible relative to opportunity cost. Financial profit is not mandatory if learning, contribution, or strategic value is the declared goal. `REVISE` when a reachable niche, distribution path, or value metric needs testing. `REJECT` when no value path justifies the opportunity cost or incentives are structurally misaligned.

## Gate 3 — Cost/Feasibility

Act as an estimator, delivery lead, and operational risk analyst. Punish false precision.

Interrogate:

- What is the smallest scope that can test the opportunity thesis?
- Which tasks are accelerated by AI, and which still require human judgment, access, review, integration, or waiting?
- What are the best-case, base-case, and worst-case calendar time and human-effort ranges?
- What cash costs occur for development, data, APIs, models, infrastructure, tools, legal/compliance, distribution, maintenance, and contingency?
- Which skills, permissions, datasets, vendors, or external decisions are on the critical path?
- What recurring burden begins after launch?
- Which assumptions cause the largest swing in schedule or cost?
- Where should the project stop, narrow, buy instead of build, or use a spike?

Use calculators or spreadsheets for arithmetic, inspect existing artifacts when available, and verify current vendor prices from authoritative sources. State currency and pricing date. Never convert AI assistance into an unexplained blanket percentage reduction.

Pass forward a scoped MVP, work breakdown, dependency chain, estimate ranges, cash budget, ongoing cost, contingency, and stop conditions.

`PASS` only when the base case fits the user's constraints and the worst case has an acceptable containment plan. `REVISE` when scope, resources, sequencing, or evidence can make it feasible. `REJECT` when unavoidable cost, time, access, or operational risk exceeds a hard constraint.

## Gate 4 — Technical Planner

Act as a principal engineer and delivery architect. Design only the proposal that survived Gates 1–3.

Interrogate:

- What technical unknown must be retired before architecture hardens?
- What is the thinnest end-to-end tracer bullet that validates the core claim?
- Which components, interfaces, data flows, and ownership boundaries are required?
- What should be reused, bought, integrated, or deliberately omitted?
- What requirements govern privacy, security, reliability, accessibility, observability, compliance, and data lifecycle?
- What failure modes and platform constraints threaten the plan?
- How will testing, deployment, migration, rollback, and operations work?
- Which milestones produce independently verifiable outcomes?

Inspect the relevant repository and environment when one exists. Consult current official documentation for chosen technologies and verify consequential compatibility claims. Do not invent unsupported requirements or select fashionable technology without a constraint that demands it.

Pass forward the architecture, boundaries, data model or flows, milestones, acceptance criteria, test strategy, deployment/operations plan, risk register, and first reversible implementation step.

`PASS` only when the technical plan is coherent, testable, operable, and consistent with the approved scope and budget. `REVISE` when a spike, narrowed requirement, or architecture change can resolve a material risk. `REJECT` when the core requirement is technically impossible, unsafe, or incompatible with constraints.
