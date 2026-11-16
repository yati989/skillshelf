# SkillShelf

**Reusable agent skills for learning, understanding code, and thinking through ideas.**

SkillShelf is a collection of 17 workflows developed for personal use and packaged for others to adapt. Read a book with source references, learn engineering concepts from an actual repository, practise explaining a topic, or pressure-test an idea before building it.

A skill is a folder of instructions and optional helpers that a coding agent can load. The agent supplies the reasoning and tool access; SkillShelf supplies the workflow. This collection is prepared for Codex. Other agents may use the Markdown instructions, but discovery, invocation, metadata, and tool compatibility have not been verified for them.

## Start with one skill

Clone the collection into a location you will keep:

```bash
git clone https://github.com/yati989/skillshelf.git
cd skillshelf
python3 scripts/install.py tutor-plain-language
```

The installer copies selected skills into `~/.agents/skills` and includes their SkillShelf companions. It refuses to overwrite existing folders. It does not modify your approved profile or install Python packages. Keep this checkout for skills that use the bundled learning runtime.

Restart or reload your agent so it discovers the new skill, then try:

```text
Use $tutor-plain-language to explain this function with a tiny example.
```

List available skills or install the whole collection:

```bash
python3 scripts/install.py --list
python3 scripts/install.py --all
```

If a skill already exists, the command reports the conflict before copying anything. Review the existing version before replacing it yourself. [Installation and runtime setup](docs/setup.md) explains dependencies and manual installation.

## Browse the shelf

### Learning

| Skill | What it does | Setup |
| --- | --- | --- |
| [interviewer-agent](skills/interviewer-agent/SKILL.md) | Practise concept-first interviews with bounded transfer probes and saved feedback. | Agent only |
| [language-tutor](skills/language-tutor/SKILL.md) | Build and resume a spoken-language course with practice and assessments. | Python + personal context |
| [personal-context](skills/personal-context/SKILL.md) | Manage a shared personal profile through exact proposals and explicit approval. | Bundled learning runtime |
| [reading-agent](skills/reading-agent/SKILL.md) | Read supplied books or passages in source-grounded parts with checkpoints. | Bundled learning runtime |
| [student-agent](skills/student-agent/SKILL.md) | Practise learning by teaching a curious student who probes your explanation. | Agent only |
| [tutor-codebase](skills/tutor-codebase/SKILL.md) | Teach transferable engineering concepts from real code and preserve completed lessons. | Personal context companion |
| [tutor-source-grounded](skills/tutor-source-grounded/SKILL.md) | Build a persistent evidence base, teach from approved sources, and assess understanding. | Bundled learning runtime |

### Code understanding

| Skill | What it does | Setup |
| --- | --- | --- |
| [code-concept-map](skills/code-concept-map/SKILL.md) | Build an interactive tree of concepts actually used in a repository. | Python for HTML renderer |
| [code-execution-path](skills/code-execution-path/SKILL.md) | Trace a task through a concise chain of linked execution steps. | Agent only |
| [structure-map](skills/structure-map/SKILL.md) | Map a library's main abstractions and everyday entry points. | Agent only |
| [tutor-code-file](skills/tutor-code-file/SKILL.md) | Explain one code file through its purpose, structure, and execution flow. | Agent only |
| [tutor-plain-language](skills/tutor-plain-language/SKILL.md) | Explain a bounded piece of code or prose in clear, concrete language. | Agent only |
| [tutor-visual](skills/tutor-visual/SKILL.md) | Explain code, architecture, and data flow with grounded visualizations. | Agent only |

### Coding

| Skill | What it does | Setup |
| --- | --- | --- |
| [auto-complete](skills/auto-complete/SKILL.md) | Turn comments, pseudocode, or broken code into a working implementation. | Agent only |

### Thinking

| Skill | What it does | Setup |
| --- | --- | --- |
| [brainstorming-agent](skills/brainstorming-agent/SKILL.md) | Explore ideas, test assumptions, and compare options through discussion. | Agent only |
| [idea-council-agent](skills/idea-council-agent/SKILL.md) | Evaluate an idea through four sequential expert gates. | Subagents + web research |
| [self-help-agent](skills/self-help-agent/SKILL.md) | Offer explicitly requested, research-informed supportive conversation. | Agent only |

## A few ways to use it

```text
Use $student-agent. I will explain database indexes; ask about gaps in my reasoning.

Use $code-execution-path to trace what happens when this API receives a request.

Use $reading-agent to read this PDF with me, one chapter at a time.

Use $brainstorming-agent to compare two approaches to this side project.
```

See [example requests for every skill](docs/examples.md). Skills keep their existing invocation policies; installing the collection does not make every workflow run automatically.

## What is included

```text
skills/       Each skill's instructions, references, metadata, and helpers
runtime/      Python tools for source processing, reading, learning records, and profile approvals
scripts/      Selective installation and collection validation
catalog.json  Skill descriptions, examples, and companion dependencies
docs/         Setup, examples, and distribution provenance
```

Instruction-only skills need a coding agent with the appropriate file and conversation tools. Python helpers and the learning runtime require Python 3.9+. The council skill needs subagents and research tools. Browsing, voice, OCR, and specialized visualization features depend on what your agent environment provides; installing a skill does not add those capabilities.

Learning records, supplied books, interview reports, and approved personal facts belong in your own private locations. The repository includes reusable behavior and code, without the author's personal notes, question bank, or completed learning records. Source-grounded learning distinguishes source claims from generated examples and preserves assessment attempts; a completed lesson is not automatically proof of mastery.

## Related project and provenance

[Job Atlas](https://github.com/yati989/job-atlas) contains the job-search, resume, and outreach workflows. Those skills are deliberately excluded here, along with installed third-party skills from Matt Pocock's collection. See [distribution provenance](docs/provenance.md).

## Development

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
cd runtime
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Collection validation checks packaged files, catalog consistency, local Markdown links, Python syntax, and accidental inclusion of known private or excluded artifacts. It does not establish teaching quality or verify every workflow in every agent environment.

## License

[MIT](LICENSE). Supplied books and other user-provided sources retain their own licenses; they are not included in this distribution.
