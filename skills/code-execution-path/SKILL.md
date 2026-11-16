---
name: code-execution-path
description: Show any requested task as a concise, linked chain of its actual execution steps without explanation.
---

# Code Execution Path

For the task the user names, inspect only enough local code, commands, and
app/tool documentation to identify its real execution path.

Return only one linear arrow chain. Each node is a short label linked to the
concrete implementation entry point: a local file and line number, an invoked
command, or an authoritative tool/API page. Use no headings, bullets,
explanations, caveats, or code blocks.

Include the user-visible input, the substantive processing steps, and the
final output/destination. Do not execute the task or make any external write.
