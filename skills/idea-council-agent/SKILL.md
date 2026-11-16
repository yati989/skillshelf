---
name: idea-council-agent
description: "Evaluate and debate a proposed project through a sequential adversarial council: Philosopher/Critic, Economics/Opportunity, Cost/Feasibility, then Technical Planner. Use when the user wants to pressure-test a project, startup, product, open-source effort, research direction, side project, or implementation idea before committing, or asks for a go/no-go decision, feasibility review, project debate, or staged expert critique."
---

# Idea Council Agent

Run one idea through four fresh expert subagents in order. Treat each gate as a veto point, not as a request for encouragement. A gate returns exactly `PASS`, `REVISE`, or `REJECT`; only `PASS` unlocks the next gate.

Read [`references/council-contract.md`](references/council-contract.md) before dispatching Gate 1. Use its Council State and Gate Record as the single source of truth.

## Council law

- Dispatch the gates sequentially: Philosopher/Critic -> Economics/Opportunity -> Cost/Feasibility -> Technical Planner. Never run them in parallel.
- Give each gate to a fresh subagent. Pass the current Council State, all prior Gate Records, the common evidence rules, and only the current gate's mandate.
- Instruct every gate to act as an independent domain expert, use relevant available tools, and try to falsify the idea's important assumptions.
- Do not let a later gate soften, reinterpret, or bypass an earlier gate's decision.
- Keep the user's original intent separate from revised versions of the proposal. Never silently rewrite the goal to make it pass.
- Treat `REVISE` as a closed gate. Ask the user the gate's decision-changing questions, record approved changes, and rerun that same gate with a fresh subagent.
- Treat `REJECT` as terminal for the current version. Stop, report the rejection case and reversal conditions, and offer to evaluate a materially revised version from Gate 1.
- If subagents are unavailable, report that the full council cannot run and ask whether the user wants a degraded single-agent version. Do not present a single-agent simulation as the four-expert council.

## 1. Build the Council State

Run a depth-first intake before Gate 1. Ask as many questions and follow-up rounds as needed to understand the idea precisely; there is no question-count or interview-length limit. Probe vague terms, contradictions, unstated assumptions, motives, intended users, real-world workflows, desired outcomes, success measures, constraints, dependencies, harms, and why this approach is preferable to doing nothing or using an existing solution.

Use the evidence rules in `references/council-contract.md` during intake. Research externally verifiable questions—especially whether similar products, projects, research, or substitutes already exist—rather than asking the user to know the market. Bring findings back to the user to clarify whether those alternatives satisfy the need and what, if anything, makes the proposal different. Continue until the user confirms the captured idea and no material ambiguity remains. Do not infer a detail merely to shorten the interview; label any unavoidable inference as an assumption and ask the user to confirm it.

Record:

- original idea and motive
- current proposal version
- intended users and problem
- desired outcomes: learning, contribution, revenue, impact, or other
- constraints: time, budget, deadline, skills, geography, policy, privacy, and dependencies
- researched alternatives, competitors, substitutes, and the user's claimed differentiation
- assumptions, unknowns, and evidence already supplied

Completion criterion: the user has confirmed the Council State; every material ambiguity is resolved or explicitly marked unknown; the initial prior-art landscape is recorded; and the Philosopher/Critic can state what must be true for the project to deserve existence.

## 2. Run a gate

Dispatch a fresh subagent with this compact brief:

1. Read the Council State, prior Gate Records, evidence rules, decision rules, and the current gate mandate in `references/council-contract.md`.
2. Challenge the proposal from the current discipline; do not merely summarize it.
3. Use relevant tools and authoritative knowledge for decision-changing claims.
4. Return one complete Gate Record and no implementation work.

When the record returns, audit it before accepting the decision:

- Every material current-world claim has evidence or is marked unverified.
- Observations, user claims, estimates, and inferences are distinguishable.
- The strongest objection is steelmanned and answered or left open.
- The decision matches the contract and names reversal conditions.
- Constraints passed forward are concrete enough for the next expert to use.

If any item fails, return the record to the same gate agent for correction. Completion criterion: one contract-compliant Gate Record is appended to the Council State.

## 3. Enforce the decision

For `PASS`, show the user a compact gate result, append the record, and dispatch the next gate.

For `REVISE`, show the blocking assumptions and the smallest decision-changing questions. Wait for the user's answers or explicit approval of a proposed revision. Add a new proposal version without deleting history, then rerun the same gate. Do not advance.

For `REJECT`, stop the sequence. Present the fatal case, evidence, credible alternatives, and conditions that would justify reconsideration. Do not produce a technical implementation plan for a rejected idea.

Completion criterion: the next action is consistent with the gate decision, with no skipped or concurrently running gate.

## 4. Deliver the verdict

After Gate 4 passes, synthesize rather than re-litigate. Deliver:

- final verdict and confidence
- one-line ledger for all four gates
- approved current proposal and explicit non-goals
- strongest surviving risks and unverified assumptions
- opportunity and cost summary, including ranges
- technical direction, milestones, validation plan, and first reversible step
- stop conditions and the next review point
- evidence links or artifact references near the claims they support

If the run ends at `REVISE` or `REJECT`, deliver the same ledger only through the stopping gate and make the next decision required from the user unmistakable.

Completion criterion: the report preserves the full decision trail, distinguishes evidence from inference, and gives exactly one recommended next action.
