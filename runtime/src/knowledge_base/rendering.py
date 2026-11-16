"""Readable derivative rendering from canonical structured documents."""

from collections import OrderedDict
from typing import Dict, List

from .models import StructuredDocument
from .storage import slugify


def split_markdown(document: StructuredDocument) -> Dict[str, str]:
    """Return deterministic source-relative Markdown files grouped by chapter."""
    groups: "OrderedDict[str, List[str]]" = OrderedDict()
    for block in document.blocks:
        chapter = block.heading_path[0] if block.heading_path else "Unsectioned"
        groups.setdefault(chapter, [])
        marker = "<!-- {0} -->".format(block.location)
        if block.kind == "heading":
            level = max(1, len(block.heading_path))
            value = "{0} {1}".format("#" * min(6, level), block.text)
        else:
            value = block.text
        groups[chapter].extend([marker, value])

    artifacts: Dict[str, str] = {}
    links: List[str] = ["# {0}".format(document.title), ""]
    for index, (chapter, parts) in enumerate(groups.items(), start=1):
        filename = "{0:03d}-{1}.md".format(index, slugify(chapter))
        links.append("- [{0}]({1})".format(chapter, filename))
        artifacts[filename] = "\n\n".join(parts).rstrip() + "\n"
    artifacts["index.md"] = "\n".join(links).rstrip() + "\n"
    return artifacts
