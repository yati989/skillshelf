# Installation and dependencies

## Requirements

Use a coding agent that can read skill folders, inspect local files, and run commands. The collection is prepared for Codex; support for other hosts has not been verified. Use Python 3.9+ for the installer and Python helpers. Your agent's account, tool access, and usage costs are separate.

## Select skills

From a persistent checkout of SkillShelf:

```bash
python3 scripts/install.py --list
python3 scripts/install.py student-agent tutor-plain-language
python3 scripts/install.py reading-agent
```

The last command includes `personal-context` as a companion. The default destination is `~/.agents/skills`. Existing folders cause the whole install to stop before copying. `--dest PATH` supports isolated testing or a host with a different discovery directory; it is not needed for the standard installation.

For a manual install, copy each complete folder from `skills/` into `~/.agents/skills`, including its companions listed in `catalog.json`. Do not copy personal notes into installed skill folders. Restart or reload the agent after installation. Use a prompt such as `Use $student-agent ...`.

## Learning runtime

The installer writes local `project.json` pointers for `reading-agent` and `personal-context`, referencing this checkout's `runtime/`. An alternative compatible Knowledge Base source checkout may be selected with `--knowledge-base PATH`. Keep that checkout available after installation; moving it requires updating the local pointers or setting `KNOWLEDGE_BASE_PROJECT`.

For manual installation, set `KNOWLEDGE_BASE_PROJECT` to the absolute path of `runtime/`, or use the launcher's `--project PATH` option. The value must name a directory containing `src/knowledge_base/`.

Try help before initializing any personal data:

```bash
python3 ~/.agents/skills/reading-agent/scripts/read.py --help
python3 ~/.agents/skills/personal-context/scripts/context.py --help
```

The source-grounded tutor uses `kb-tutor`. Install it in the runtime's dedicated virtual environment:

```bash
cd runtime
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/kb-tutor --help
```

Activate that environment when using `kb-tutor`, or run its full path. Alternatively run `PYTHONPATH=src python3 -m knowledge_base` from `runtime/`. Tell the agent which runtime environment to use. For PDF processing, install `.[pdf]` in that same environment; see [runtime details](../runtime/README.md).

Installing skills does not initialize a profile or approve profile changes. Profile storage belongs to the user under `~/.codex/personal-context`; skill instructions require exact proposals and separate approval for permanent changes. Reading workspaces, course records, and knowledge books are private data and should not be shared with the skill repository.

## Other helpers and tools

- `language-tutor` uses its bundled standard-library `scripts/course.py` and the `personal-context` companion. It cannot create voice access; spoken feedback requires actual audio evidence.
- `code-concept-map` includes its HTML viewer and Python renderer. Inspect the renderer's `--help` for its input format.
- `idea-council-agent` needs subagent delegation and research tools. When unavailable, the skill requires disclosure and a decision about a reduced workflow.
- `tutor-visual` uses visualization capabilities available in the host. It does not install a visualization plugin. Keep its saved lessons in the same private knowledge book as `tutor-codebase` when both are used.
- `interviewer-agent` accepts supplied roles, descriptions, resumes, projects, or an explicitly configured question bank. No private question bank is shipped.
- `self-help-agent` provides AI support, not professional mental-health care. Research and local support tools depend on the host.

## Updating

Pull the new repository version, inspect the differences, and back up your installed skill before manually replacing it. The installer intentionally has no overwrite mode. Keep learner data outside installed skills so updates do not replace personal records.
