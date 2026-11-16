# Learning runtime

This is the deterministic Python runtime used by SkillShelf's reading, source-grounded tutoring, and personal-context skills. It handles source versions, document extraction, retrieval, durable learning records, and exact-proposal profile approval. The agent performs teaching and synthesis.

Python 3.9+ is required. Base commands use the standard library. From this directory:

```bash
PYTHONPATH=src python3 -m knowledge_base --help
PYTHONPATH=src python3 -m knowledge_base.reading_cli --help
PYTHONPATH=src python3 -m knowledge_base.personal_context_cli --help
```

To install console commands in a dedicated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

For PDFs, use the `pdf` extra (`.venv/bin/python -m pip install -e '.[pdf]'`). Poppler can serve as a system-installed fallback. Difficult-page recovery optionally uses `.[pdf,difficult-pdf]` on Python 3.10+. No OCR or embedding service is required for basic text processing; advanced providers must be explicitly configured.

The reading launcher defaults to `.kb-workspace` in this runtime directory. Pass `--root` for another private workspace. The personal-context runtime defaults to `~/.codex/personal-context`; setup does not populate it. Keep both outside version control. Never commit books, learner responses, or personal facts.

Run existing runtime tests with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v`. Test-generated records use temporary directories.
