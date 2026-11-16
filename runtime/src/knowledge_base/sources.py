"""Approved source acquisition and conversion adapters."""

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from .models import DocumentBlock, SourceCandidate, StructuredDocument
from .pdf_processing import (
    PDFIngestor,
    PDFProcessingError,
    PopplerBackend,
    PopplerPageFallback,
    DoclingPageFallback,
    RunCommand,
    _run_command,
)


class SourceProcessingError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in Path(path).rglob("*") if candidate.is_file()):
        relative = item.relative_to(path)
        if ".git" in relative.parts:
            continue
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        with item.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def paragraphs(text: str) -> List[Tuple[int, int, str]]:
    results: List[Tuple[int, int, str]] = []
    start: Optional[int] = None
    buffer: List[str] = []
    lines = text.splitlines()
    for number, line in enumerate(lines, start=1):
        if line.strip():
            if start is None:
                start = number
            buffer.append(line.rstrip())
        elif buffer:
            results.append((start or number, number - 1, "\n".join(buffer)))
            start = None
            buffer = []
    if buffer:
        results.append((start or len(lines), len(lines), "\n".join(buffer)))
    return results


class TextAdapter:
    source_types = {"text", "markdown", "transcript"}

    def convert(self, source: SourceCandidate, path: Path) -> Tuple[StructuredDocument, str]:
        text = path.read_text(encoding="utf-8")
        blocks: List[DocumentBlock] = []
        current_section: Optional[str] = None
        heading_path: List[str] = []
        for index, (start, end, value) in enumerate(paragraphs(text), start=1):
            first_line = value.splitlines()[0].strip()
            is_heading = first_line.startswith("#")
            if is_heading:
                current_section = first_line.lstrip("#").strip()
                level = len(first_line) - len(first_line.lstrip("#"))
                heading_path = heading_path[: level - 1] + [current_section]
            blocks.append(
                DocumentBlock(
                    block_id="b{0:05d}".format(index),
                    kind="heading" if is_heading else "paragraph",
                    text=value,
                    location="lines:{0}-{1}".format(start, end),
                    section=current_section,
                    heading_path=list(heading_path),
                )
            )
        document = StructuredDocument(
            source_id=source.source_id,
            title=source.title,
            source_type=source.source_type,
            source_hash=sha256_file(path),
            metadata={"filename": path.name, "encoding": "utf-8"},
            blocks=blocks,
        )
        return document, text.rstrip() + "\n"


class _ReadableHTML(HTMLParser):
    block_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self._tag: Optional[str] = None
        self._parts: List[str] = []
        self.blocks: List[Tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        if tag in self.block_tags:
            self._tag = tag
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._tag:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._tag == tag:
            value = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            if value:
                self.blocks.append((tag, value))
            self._tag = None
            self._parts = []


class HTMLAdapter:
    source_types = {"html", "web", "web-book", "standard"}

    def convert(self, source: SourceCandidate, path: Path) -> Tuple[StructuredDocument, str]:
        parser = _ReadableHTML()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        blocks: List[DocumentBlock] = []
        markdown: List[str] = []
        section: Optional[str] = None
        heading_path: List[str] = []
        for index, (tag, value) in enumerate(parser.blocks, start=1):
            is_heading = tag.startswith("h") and len(tag) == 2 and tag[1].isdigit()
            if is_heading:
                section = value
                level = int(tag[1])
                heading_path = heading_path[: level - 1] + [value]
                markdown.append("{0} {1}".format("#" * level, value))
            elif tag == "li":
                markdown.append("- {0}".format(value))
            elif tag == "pre":
                markdown.append("```\n{0}\n```".format(value))
            else:
                markdown.append(value)
            blocks.append(
                DocumentBlock(
                    block_id="b{0:05d}".format(index),
                    kind="heading" if is_heading else "paragraph",
                    text=value,
                    location="html-block:{0}".format(index),
                    section=section,
                    heading_path=list(heading_path),
                    confidence=0.9,
                )
            )
        warnings = [] if blocks else ["No readable HTML blocks were extracted"]
        document = StructuredDocument(
            source_id=source.source_id,
            title=source.title,
            source_type=source.source_type,
            source_hash=sha256_file(path),
            metadata={"filename": path.name},
            blocks=blocks,
            warnings=warnings,
        )
        return document, "\n\n".join(markdown).rstrip() + "\n"


class RepositoryAdapter:
    """Converts readable documentation files from an immutable repository copy."""

    source_types = {"repository"}
    readable_suffixes = {".html", ".htm", ".md", ".markdown", ".rst", ".txt"}

    def convert(self, source: SourceCandidate, path: Path) -> Tuple[StructuredDocument, str]:
        blocks: List[DocumentBlock] = []
        markdown: List[str] = []
        warnings: List[str] = []
        block_number = 0
        readable_files = [
            item
            for item in sorted(path.rglob("*"))
            if item.is_file()
            and item.suffix.lower() in self.readable_suffixes
            and ".git" not in item.relative_to(path).parts
        ]
        for item in readable_files:
            relative = item.relative_to(path)
            try:
                text = item.read_text(encoding="utf-8")
            except UnicodeError:
                warnings.append("Could not decode {0} as UTF-8".format(relative))
                continue
            markdown.append("<!-- source-file: {0} -->".format(relative))
            current_section: Optional[str] = None
            heading_path: List[str] = []
            if item.suffix.lower() in {".html", ".htm"}:
                parser = _ReadableHTML()
                parser.feed(text)
                for file_block, (tag, value) in enumerate(parser.blocks, start=1):
                    block_number += 1
                    is_heading = tag.startswith("h") and len(tag) == 2 and tag[1].isdigit()
                    if is_heading:
                        current_section = value
                        level = int(tag[1])
                        heading_path = heading_path[: level - 1] + [value]
                        markdown.append("{0} {1}".format("#" * level, value))
                    elif tag == "li":
                        markdown.append("- {0}".format(value))
                    elif tag == "pre":
                        markdown.append("```\n{0}\n```".format(value))
                    else:
                        markdown.append(value)
                    blocks.append(
                        DocumentBlock(
                            block_id="b{0:05d}".format(block_number),
                            kind="heading" if is_heading else "paragraph",
                            text=value,
                            location="file:{0}:html-block:{1}".format(
                                relative, file_block
                            ),
                            section=current_section,
                            heading_path=list(heading_path),
                            confidence=0.9,
                        )
                    )
                continue
            for start, end, value in paragraphs(text):
                block_number += 1
                lines = value.splitlines()
                markdown_heading = lines[0].lstrip("#").strip() if lines[0].startswith("#") else None
                rst_heading = (
                    lines[0].strip()
                    if len(lines) == 2
                    and lines[1].strip()
                    and len(set(lines[1].strip())) == 1
                    and lines[1].strip()[0] in "=-~^"
                    else None
                )
                heading = markdown_heading or rst_heading
                if heading:
                    current_section = heading
                    if markdown_heading:
                        level = len(lines[0]) - len(lines[0].lstrip("#"))
                    else:
                        level = {"=": 1, "-": 2, "~": 3, "^": 4}.get(
                            lines[1].strip()[0], 2
                        )
                    heading_path = heading_path[: level - 1] + [heading]
                blocks.append(
                    DocumentBlock(
                        block_id="b{0:05d}".format(block_number),
                        kind="heading" if heading else "paragraph",
                        text=value,
                        location="file:{0}:lines:{1}-{2}".format(relative, start, end),
                        section=current_section,
                        heading_path=list(heading_path),
                        confidence=0.95,
                    )
                )
                markdown.append(("## " + heading) if heading else value)
        if not blocks:
            warnings.append("No readable Markdown, RST, or text files were extracted")
        revision = None
        revision_path = path / ".source-revision"
        if revision_path.exists():
            revision = revision_path.read_text(encoding="utf-8").strip()
        document = StructuredDocument(
            source_id=source.source_id,
            title=source.title,
            source_type=source.source_type,
            source_hash=sha256_tree(path),
            metadata={
                "directory": path.name,
                "revision": revision,
                "readable_file_count": len(readable_files),
            },
            blocks=blocks,
            warnings=warnings,
        )
        return document, "\n\n".join(markdown).rstrip() + "\n"


class PDFAdapter:
    """Compatibility-facing adapter backed by the routed PDF ingestion module."""

    source_types = {"pdf", "paper"}

    def __init__(
        self,
        runner: RunCommand = _run_command,
        ocr_provider=None,
        ingestor: Optional[PDFIngestor] = None,
    ):
        page_fallback = ocr_provider
        if page_fallback is None and importlib.util.find_spec("docling") is not None:
            page_fallback = DoclingPageFallback()
        if (
            page_fallback is None
            and runner is _run_command
            and shutil.which("pdftotext")
        ):
            page_fallback = PopplerPageFallback(runner)
        self.ingestor = ingestor or PDFIngestor(
            compatibility=PopplerBackend(runner), page_fallback=page_fallback
        )

    def convert(self, source: SourceCandidate, path: Path) -> Tuple[StructuredDocument, str]:
        try:
            return self.ingestor.convert(source, path, sha256_file(path))
        except PDFProcessingError as error:
            raise SourceProcessingError(str(error)) from error


class SourceProcessor:
    """Acquires an approved source and routes it to a conversion adapter."""

    def __init__(self) -> None:
        adapters = [TextAdapter(), HTMLAdapter(), PDFAdapter(), RepositoryAdapter()]
        self.adapters = {
            source_type: adapter
            for adapter in adapters
            for source_type in adapter.source_types
        }

    def acquire(self, source: SourceCandidate, originals_dir: Path) -> Path:
        originals_dir.mkdir(parents=True, exist_ok=True)
        parsed = urllib.parse.urlparse(source.uri)
        if source.source_type == "repository" and parsed.scheme in {"http", "https"}:
            repository_url = urllib.parse.urlunparse(parsed._replace(fragment=""))
            revision = parsed.fragment or "HEAD"
            temporary = originals_dir / ("." + source.source_id + "-clone")
            if temporary.exists():
                shutil.rmtree(str(temporary))
            command = ["git", "clone", "--depth", "1"]
            if revision != "HEAD":
                command.extend(["--branch", revision])
            command.extend([repository_url, str(temporary)])
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
                result = subprocess.run(
                    ["git", "-C", str(temporary), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                if temporary.exists():
                    shutil.rmtree(str(temporary))
                raise SourceProcessingError("Repository acquisition failed: {0}".format(error)) from error
            resolved_revision = result.stdout.strip()
            shutil.rmtree(str(temporary / ".git"))
            (temporary / ".source-revision").write_text(
                resolved_revision + "\n", encoding="utf-8"
            )
            destination = originals_dir / (
                source.source_id + "-" + resolved_revision[:12]
            )
            if destination.exists():
                shutil.rmtree(str(temporary))
            else:
                os.replace(str(temporary), str(destination))
            return destination
        if parsed.scheme in {"http", "https"}:
            suffix = Path(parsed.path).suffix or (".html" if source.source_type == "web" else ".bin")
            request = urllib.request.Request(
                source.uri, headers={"User-Agent": "source-grounded-learning/0.1"}
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
            content_hash = hashlib.sha256(content).hexdigest()
            destination = originals_dir / (
                source.source_id + "-" + content_hash[:12] + suffix.lower()
            )
            if not destination.exists():
                destination.write_bytes(content)
            return destination

        source_path = Path(source.uri).expanduser().resolve()
        if source.source_type == "repository" and source_path.is_dir():
            content_hash = sha256_tree(source_path)
            destination = originals_dir / (source.source_id + "-" + content_hash[:12])
            if not destination.exists():
                shutil.copytree(str(source_path), str(destination), ignore=shutil.ignore_patterns(".git"))
            return destination
        if not source_path.is_file():
            raise SourceProcessingError("Source file does not exist: {0}".format(source_path))
        content_hash = sha256_file(source_path)
        destination = originals_dir / (
            source.source_id + "-" + content_hash[:12] + source_path.suffix.lower()
        )
        if source_path != destination:
            shutil.copy2(str(source_path), str(destination))
        return destination

    def process(
        self, source: SourceCandidate, originals_dir: Path
    ) -> Tuple[Path, StructuredDocument, str]:
        adapter = self.adapters.get(source.source_type)
        if adapter is None:
            raise SourceProcessingError(
                "Unsupported source type: {0}".format(source.source_type)
            )
        acquired = self.acquire(source, originals_dir)
        document, markdown = adapter.convert(source, acquired)
        return acquired, document, markdown
