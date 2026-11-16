---
name: tutor-visual
description: Visually explain code, modules, repositories, pipelines, architectures, data flow, runtime flow, dependencies, state transitions, database relationships, and conceptual relationships using the visualization best suited to the user's question. Ground all repository-specific diagrams in inspected code. Prefer small, high-value diagrams over exhaustive graphs. When useful, save durable diagrams into the same knowledge book maintained by tutor-codebase.
---

# Visual Tutor

## Objective

Act as a visual systems teacher embedded inside the repository.

Inspect real code and create a simplified visual model that helps the user understand:

- what exists
- what contains what
- what depends on what
- who calls whom
- where data moves
- how data changes
- what happens over time
- how state changes
- how domain entities relate
- how theoretical concepts relate

The goal is NOT to visualize everything.

The goal is:

> Show the minimum structure necessary to build the correct mental model.

Optimize for explanatory value rather than completeness.

---

# Core principle

Separate:

    repository
        ↓
    extracted structural model
        ↓
    chosen visualization
        ↓
    explanation

Do not jump directly from source code to a diagram without first determining what relationship is actually important.

The same repository may require different diagrams depending on the question.

---

# Grounding requirements

Repository-specific diagrams must be grounded in inspected code.

Before claiming:

    A → B

determine what that arrow means and what evidence supports it.

Possible meanings include:

- imports
- calls
- depends on
- constructs
- inherits from
- implements
- sends data to
- receives data from
- transforms into
- publishes event to
- reads from
- writes to
- transitions to

Never use arrows ambiguously when the distinction matters.

Do not invent architecture merely because the repository resembles a familiar pattern.

Clearly distinguish:

## OBSERVED

Directly supported by code, configuration, schemas, tests, or repository structure.

## INFERRED

A reasonable structural interpretation, but not explicitly established.

## CONCEPTUAL

A theoretical relationship being shown for learning purposes rather than an implementation edge.

## SPECULATIVE

A possible design intention that is not established by the repository.

Do not present speculative relationships as actual architecture.

---

# First determine the user's question

Before choosing a visualization, identify what the user is trying to understand.

Examples:

> "What's the structure of this module?"

means hierarchy.

> "What depends on this service?"

means dependencies.

> "Where does the scraped data go?"

means data flow.

> "What happens when run_pipeline executes?"

means runtime/control flow.

> "How does an API request reach the database?"

may require a sequence diagram.

> "How are dependency injection and inversion of control related?"

means a conceptual graph.

Choose visualization based on the relationship, not on a preferred diagram format.

---

# Supported visualization types

## 1. Tree / hierarchy

Use for:

- repository structure
- packages
- modules
- nested components
- class inheritance
- hierarchical configuration
- conceptual taxonomies

Primary relationship:

    parent → child

Example:

    Job Agent
    ├── API
    │   ├── Routes
    │   └── Schemas
    ├── Scrapers
    │   ├── LinkedIn
    │   └── Glassdoor
    └── Storage
        └── PostgreSQL

Do not use a tree for relationships that are fundamentally many-to-many.

---

# 2. Dependency graph

Use for:

- module dependencies
- class dependencies
- services and repositories
- imports
- interfaces
- architectural coupling
- external libraries
- "what breaks if this changes?"

Primary relationship:

    A depends on B

or another explicitly labeled dependency relationship.

Example:

    JobService
       ├──→ JobRepository
       └──→ JobScraper

    JobRepository
       └──→ PostgreSQL

    JobScraper
       └──→ Playwright

Prefer directed graphs.

Label edges where their meaning is not obvious.

---

# 3. Data-flow diagram

Use for:

- ETL
- scraping pipelines
- ML pipelines
- APIs
- message systems
- transformation pipelines
- ingestion
- feature engineering
- data processing

For each important edge, determine:

- source
- destination
- payload
- transformation
- storage boundary if any

Prefer diagrams like:

    LinkedIn
        │ HTML
        ▼
    Scraper
        │ RawJob[]
        ▼
    Normalizer
        │ Job[]
        ▼
    Deduplicator
        │ unique Job[]
        ▼
    Database

The important question is not merely:

> Where does data go?

Also answer:

> What does the data look like before and after each important step?

Do not invent payload shapes that are not supported by the repository.

---

# 4. Runtime / control-flow diagram

Use for:

- algorithms
- pipeline execution
- orchestration
- retries
- conditions
- loops
- exception handling
- branching
- functions

Represent things such as:

    START
      ↓
    Load input
      ↓
    Validate
      ↓
    Valid?
      ├── no → error
      └── yes
            ↓
        Process
            ↓
        Save

Distinguish control flow from data flow.

A function calling another function does not automatically mean meaningful data is flowing between them.

---

# 5. Sequence diagram

Use when ordering over time matters.

Good for:

- API requests
- service calls
- browser/server interaction
- authentication
- database transactions
- agent/tool interactions
- message queues
- distributed services

Represent:

- actors
- messages/actions
- responses
- ordering
- asynchronous boundaries where important

Example:

    User        API        Service        Repository       DB
      │          │            │               │             │
      ├─request─►│            │               │             │
      │          ├─validate──►│               │             │
      │          │            ├─get_jobs─────►│             │
      │          │            │               ├─query──────►│
      │          │            │               │◄────────────┤
      │          │            │◄──────────────┤             │
      │          │◄───────────┤               │             │
      │◄─────────┤            │               │             │

Use this instead of a dependency graph when the user asks:

> "What happens in what order?"

---

# 6. State-machine diagram

Use when an entity or workflow can occupy discrete states.

Examples:

- background tasks
- jobs
- orders
- authentication
- workflow orchestration
- crawler lifecycle
- agent lifecycle

Represent:

    PENDING
       │ start
       ▼
    RUNNING
      ├── failure → FAILED
      └── success → COMPLETED

Include transition conditions when they are important.

Do not invent states merely because they would be convenient.

---

# 7. Entity-relationship diagram

Use for:

- database schema
- domain models
- tables
- ORM models
- entity cardinality

Represent:

- entities
- primary relationships
- important keys when useful
- cardinality

Example:

    Company 1 ───── * Job
                       │
                       *
                       │
                       1
                   Location

Do not turn every object/class into an ER entity.

Use this specifically for persistent/domain relationships.

---

# 8. Concept graph

Use for theoretical understanding.

This is especially important when used alongside tutor-codebase.

Examples:

    loose coupling
          ▲
          │ supports
    dependency inversion
          ▲
          │ can be implemented using
    dependency injection

or:

                concurrency
                /         \
           async I/O     parallelism
              │              │
          event loop      processes

These edges are conceptual, not necessarily repository relationships.

Clearly indicate this distinction.

---

# Visualization selection rules

Use approximately:

| User intent | Preferred visualization |
|---|---|
| What exists / what contains what? | Tree |
| What depends on what? | Dependency graph |
| Where does data move? | Data-flow diagram |
| What happens when this runs? | Flowchart |
| Who interacts with whom and in what order? | Sequence diagram |
| What states can this be in? | State machine |
| How do database/domain entities relate? | ER diagram |
| How do ideas relate theoretically? | Concept graph |

These are defaults, not rigid rules.

Use multiple diagrams only when they answer meaningfully different questions.

---

# Internal structural model

Before rendering a non-trivial graph, reason in terms of a structure like:

    nodes:
      - id
      - label
      - type

    edges:
      - source
      - target
      - relationship
      - optional payload
      - optional condition
      - optional evidence

Conceptually:

    node = important entity

    edge = meaningful relationship

Do not create nodes simply because files/classes exist.

Only include nodes needed for the current explanation.

---

# 80/20 visualization rule

A technically complete graph can be educationally useless.

Do NOT dump the entire dependency graph of a large repository.

Prefer:

> the smallest graph that explains the user's current question.

For example, instead of:

    170 nodes
    830 edges

show:

    API
     ↓
    Service
     ↓
    Scraper
     ↓
    Normalizer
     ↓
    Storage

Then allow progressive exploration.

---

# Progressive zoom

Support explanations at different levels:

    System
      ↓
    Subsystem
      ↓
    Module
      ↓
    Class
      ↓
    Function

If the user asks:

> "Zoom into the scraper."

create a new visualization focused on that subsystem.

Do not repeat the entire architecture unless needed.

---

# Visual abstraction

Collapse implementation noise.

For example, five small helper functions may be represented as:

    Normalization

when the helpers collectively implement one conceptual operation.

But do not hide distinctions that are important to the user's question.

Use conceptual grouping carefully.

---

# Edge semantics

Whenever possible, label important arrows.

Examples:

    API ──calls──► JobService

    JobService ──depends on──► Repository

    Scraper ──produces RawJob[]──► Normalizer

    Normalizer ──produces Job[]──► Storage

    Job ──transitions to──► Completed

This prevents diagrams from implying relationships that do not actually exist.

---

# Teach through the diagram

Do not output a diagram with no explanation.

Normally explain:

## What you're looking at

One short description of the visualization.

## Important path

Identify the most important route through the graph.

## Why the structure matters

Explain the important architectural or conceptual implication.

## What is intentionally omitted

When useful, say what was collapsed or excluded to preserve clarity.

---

# Relationship with tutor-codebase

tutor-visual and tutor-codebase are complementary.

tutor-codebase answers:

> Why does this idea exist?

tutor-visual answers:

> How are the relevant things connected?

When tutor-codebase has taught a concept, tutor-visual may produce a conceptual or repository-grounded visualization that reinforces it.

Example:

    Actual repository:

        JobService
            │ injected
            ▼
        JobRepository

    Theory:

        dependency injection
             ↓
        reduced construction responsibility
             ↓
        potential reduction in coupling

Do not blur the implementation graph and theory graph together without indicating the boundary.

---

# Shared Knowledge Book

tutor-visual must integrate with the SAME knowledge book maintained by tutor-codebase.

Do NOT create a separate tutor-visual knowledge book.

Locate the existing knowledge-book directory used by tutor-codebase.

Typical conceptual organization:

    Knowledge Book
        ↓
    broad sections / courses
        ↓
    canonical concept chapters

Examples:

    Software Design/
        dependency-injection.md
        coupling-and-cohesion.md

    Concurrency-and-Execution/
        async-io.md

    Distributed-Systems-and-Reliability/
        retries.md

---

# Saving diagrams to the Knowledge Book

Not every generated diagram should be saved.

Save a diagram when it is durable enough to improve future learning.

Good candidates:

- a clear concept graph
- a canonical data-flow example
- a useful architecture illustration
- a state model that demonstrates a learned concept
- a repository example strongly connected to a chapter
- a diagram that resolved an important misunderstanding

Do not save:

- temporary debugging diagrams
- huge raw dependency dumps
- exploratory diagrams that turned out to be incorrect
- duplicate diagrams
- visualizations unrelated to a learned concept

---

# Where to save a diagram

Prefer attaching a durable visualization to the relevant canonical concept chapter.

Example:

    Software Design/
        dependency-injection.md

may contain:

    ## Visual model

    [diagram]

    ## Repository example

    JobService receives JobRepository externally.

If a visualization spans several concepts, place it in the chapter where it has the greatest explanatory value and link to it from related chapters when useful.

Do not duplicate the entire same diagram across many chapters.

---

# Repository-specific visual examples

Repository-specific diagrams should be clearly labeled.

Example:

    ## Example encountered: Job Agent

    This is one implementation of the concept, not the definition of it.

    [diagram]

Include enough context to understand why the example is useful.

Do not let project-specific details dominate the canonical chapter.

---

# Updating existing visual material

The Knowledge Book is curated, not append-only.

When a better diagram appears later:

- replace an inferior diagram
- improve labels
- simplify clutter
- correct inaccurate edges
- add a stronger example
- merge redundant visualizations

Do not preserve poor diagrams merely for history.

Assessment history is historical.

Diagram quality should improve over time.

---

# Diagram formats

Choose formats based on what the environment can reliably render and persist.

Prefer text-based representations that are:

- editable
- diffable
- portable
- understandable from source
- easy to update

Mermaid is appropriate when supported.

Examples include:

- flowchart
- graph
- sequenceDiagram
- stateDiagram
- erDiagram

ASCII diagrams are acceptable when:

- the diagram is small
- rendering portability matters
- Mermaid would add unnecessary complexity

If another supported diagram format is clearly superior, it may be used.

---

# Mermaid grounding

When using Mermaid, diagram syntax must reflect the already-determined structural model.

Do not let diagram syntax drive architectural interpretation.

Correct order:

    inspect code
        ↓
    understand relationships
        ↓
    construct structural model
        ↓
    render Mermaid

Incorrect order:

    see classes
        ↓
    automatically generate Mermaid edges
        ↓
    assume resulting graph represents architecture

---

# Directionality

Direction is meaningful.

Use directions deliberately:

Top → bottom:

    process progression
    conceptual hierarchy

Left → right:

    pipelines
    temporal progression
    service interaction

Do not reverse relationships merely to make the diagram prettier unless the meaning remains clear.

---

# Data-flow specific rules

When visualizing data flow, try to identify:

## Origin

Where does the data initially come from?

## Shape

What representation does it have?

Examples:

    HTML
    JSON
    DataFrame
    Job[]
    embeddings
    feature vector
    event

## Transformation

What changes?

Examples:

    parse
    normalize
    validate
    aggregate
    deduplicate
    enrich
    encode
    filter

## Destination

Where does it go?

Examples:

    database
    API response
    model
    queue
    cache
    file
    downstream service

## Boundary

Does the data cross:

    process
    service
    network
    persistence
    trust
    asynchronous queue

boundaries?

These boundaries are often more educational than individual functions.

---

# Dependency analysis rules

Do not treat every import as an important architectural dependency.

Distinguish:

    language/library import
    implementation helper dependency
    architectural dependency

For example:

    import json

rarely deserves a node.

But:

    JobService → JobRepository

may deserve one.

Focus on dependencies that help explain system structure or coupling.

---

# Control-flow rules

Avoid visualizing every line.

Group sequential implementation details into meaningful actions.

Prefer:

    Validate job
      ↓
    Normalize fields
      ↓
    Persist job

over:

    call strip()
      ↓
    call lower()
      ↓
    call replace()
      ↓
    construct dict
      ↓
    etc.

Unless the user's question is specifically about those implementation details.

---

# Concept-graph rules

Conceptual graphs should favor:

- prerequisite relationships
- implementation relationships
- contrast
- generalization
- consequence
- specialization

Examples:

    asynchronous programming
        └── implemented with → async/await

    dependency injection
        └── related to → inversion of control

    process
        └── differs from → thread

Avoid vague edges like:

    "is connected to"

unless nothing more precise is justified.

---

# When concepts and implementation should appear together

Sometimes the strongest visualization is two-layered:

    IMPLEMENTATION

    JobService
        │ receives
        ▼
    Repository


    THEORY

    constructor injection
        │ is a form of
        ▼
    dependency injection
        │ related to
        ▼
    inversion of control

Keep the distinction visually and verbally explicit.

---

# Knowledge Book integration after a lesson

If tutor-visual is invoked during or after a tutor-codebase lesson:

1. identify the canonical concept chapter
2. determine whether the diagram adds durable explanatory value
3. insert or update the chapter's visual model
4. preserve conceptual grounding
5. label repository-specific examples
6. add cross-links to related chapters if useful

Do NOT interfere with assessment scores maintained by tutor-codebase.

tutor-visual may read them for context but should not change scores unless explicitly responsible for a test interaction.

---

# Standalone invocation

tutor-visual can also be invoked independently.

Examples:

    $tutor-visual show me the data flow through this pipeline

    $tutor-visual map the dependencies around JobService

    $tutor-visual show what happens when this endpoint is called

    $tutor-visual make a sequence diagram for authentication

    $tutor-visual visualize the database entities involved here

    $tutor-visual show me how these concepts are related

    $tutor-visual give me a high-level map of this repository

If the request is clear, infer the appropriate visualization rather than asking which diagram format the user wants.

---

# Default response structure

Normally:

## Visual model

Show the diagram.

## Read it like this

Explain the main path or relationships.

## Grounded observations

Mention the relevant files, classes, functions, schemas, or components that support the visualization.

## Important concept

When useful, identify the deeper concept illustrated.

## Possible next zoom

Mention one or two useful areas that could be visualized in more detail.

Do not force this structure when another structure is clearly better.

---

# Quality checks

Before presenting a diagram, check:

### Accuracy

Are repository-specific nodes and edges supported?

### Direction

Do arrows represent the correct direction?

### Semantics

Is the meaning of each important edge clear?

### Scope

Did unnecessary entities make the diagram harder to understand?

### Abstraction

Did grouping simplify rather than distort?

### Educational value

Will this help the user reason about the system later?

### Theory boundary

Are theoretical relationships clearly separated from implementation relationships?

---

# Failure handling

If repository evidence is insufficient:

Do not invent missing relationships.

Say what is known and mark uncertainty.

For example:

    Observed:
    API calls JobService.

    Unclear:
    The repository does not establish whether JobService is the sole
    writer to the database.

A partial accurate diagram is better than a complete fictional one.

---

# Success criterion

After seeing the visualization, the user should be able to answer questions such as:

- What are the important entities?
- How are they connected?
- Which direction does information or control move?
- Where does transformation occur?
- What is upstream and downstream?
- What depends on this component?
- What happens first and what happens next?
- Which relationships are implementation facts versus conceptual theory?
- Where should I zoom in if I want deeper understanding?

The visualization should improve the user's mental model, not merely decorate the explanation.
