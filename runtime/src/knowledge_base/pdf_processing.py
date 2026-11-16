"""Hierarchical PDF ingestion behind one parser-independent interface."""

from dataclasses import dataclass, field
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Tuple

from .models import DocumentBlock, SourceCandidate, StructuredDocument


class PDFProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class OutlineEntry:
    level: int
    title: str
    page: int


@dataclass
class ExtractedPage:
    number: int
    markdown: str
    confidence: float = 0.95
    warnings: List[str] = field(default_factory=list)


@dataclass
class PDFExtraction:
    backend_id: str
    pages: List[ExtractedPage]
    outline: List[OutlineEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class PDFExtractionBackend(Protocol):
    @property
    def backend_id(self) -> str:
        ...

    def extract(self, path: Path) -> PDFExtraction:
        ...


class PageFallback(Protocol):
    @property
    def provider_id(self) -> str:
        ...

    def extract_page(self, pdf_path: Path, page_number: int) -> str:
        ...


class PyMuPDF4LLMBackend:
    """Primary adapter for born-digital PDFs; imports remain optional."""

    backend_id = "pymupdf4llm"

    def extract(self, path: Path) -> PDFExtraction:
        try:
            import pymupdf
            import pymupdf4llm
        except ImportError as error:
            raise PDFProcessingError(
                "PyMuPDF4LLM is unavailable; install the 'pdf' extra"
            ) from error

        try:
            document = pymupdf.open(str(path))
            try:
                raw_outline = document.get_toc(simple=True)
                page_count = document.page_count
                pdf_metadata = dict(document.metadata or {})
            finally:
                document.close()
            chunks = pymupdf4llm.to_markdown(
                str(path), page_chunks=True, write_images=False
            )
        except Exception as error:
            raise PDFProcessingError("PyMuPDF4LLM extraction failed: {0}".format(error)) from error

        pages: List[ExtractedPage] = []
        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata") or {}
            page_number = int(metadata.get("page_number") or index)
            text = str(chunk.get("text") or "").strip()
            warnings: List[str] = []
            confidence = 0.96
            if not text:
                warnings.append("No text extracted")
                confidence = 0.2
            elif len(text) < 40:
                warnings.append("Very little text extracted")
                confidence = 0.7
            pages.append(ExtractedPage(page_number, text, confidence, warnings))

        outline = [
            OutlineEntry(int(level), str(title).strip(), max(1, int(page)))
            for level, title, page in raw_outline
            if str(title).strip() and int(page) > 0
        ]
        pdf_metadata["page_count"] = page_count
        return PDFExtraction(
            backend_id=self.backend_id,
            pages=pages,
            outline=outline,
            metadata=pdf_metadata,
        )


RunCommand = Callable[[Sequence[str]], subprocess.CompletedProcess]


def _run_command(command: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, text=True)


class PopplerBackend:
    """Compatibility adapter used when the primary optional dependency is absent."""

    backend_id = "poppler"

    def __init__(self, runner: RunCommand = _run_command):
        self.runner = runner

    def extract(self, path: Path) -> PDFExtraction:
        if self.runner is _run_command and (
            not shutil.which("pdftotext") or not shutil.which("pdfinfo")
        ):
            raise PDFProcessingError("PDF conversion requires PyMuPDF4LLM or Poppler")
        try:
            info_result = self.runner(["pdfinfo", str(path)])
            text_result = self.runner(["pdftotext", "-layout", str(path), "-"])
        except (OSError, subprocess.CalledProcessError) as error:
            raise PDFProcessingError("Poppler extraction failed: {0}".format(error)) from error

        metadata: Dict[str, Any] = {}
        for line in info_result.stdout.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower().replace(" ", "_")] = value.strip()
        raw_pages = text_result.stdout.split("\f")
        if raw_pages and not raw_pages[-1].strip():
            raw_pages.pop()
        pages = [
            ExtractedPage(
                number=index,
                markdown=text.strip(),
                confidence=0.85 if text.strip() else 0.2,
                warnings=[] if text.strip() else ["No text extracted"],
            )
            for index, text in enumerate(raw_pages, start=1)
        ]
        return PDFExtraction(self.backend_id, pages, metadata=metadata)


class DoclingPageFallback:
    """Optional high-fidelity fallback for pages rejected by the primary parser."""

    provider_id = "docling"

    def extract_page(self, pdf_path: Path, page_number: int) -> str:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as error:
            raise PDFProcessingError("Docling is unavailable; install the 'docling' extra") from error
        try:
            result = DocumentConverter().convert(
                str(pdf_path), page_range=(page_number, page_number)
            )
            return result.document.export_to_markdown().strip()
        except Exception as error:
            raise PDFProcessingError(
                "Docling fallback failed on page {0}: {1}".format(page_number, error)
            ) from error


class PopplerPageFallback:
    """Lightweight page recovery when the primary parser yields unusable text."""

    provider_id = "poppler-page"

    def __init__(self, runner: RunCommand = _run_command):
        self.runner = runner

    def extract_page(self, pdf_path: Path, page_number: int) -> str:
        try:
            result = self.runner(
                [
                    "pdftotext",
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    "-layout",
                    str(pdf_path),
                    "-",
                ]
            )
            return result.stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise PDFProcessingError(
                "Poppler page fallback failed on page {0}: {1}".format(
                    page_number, error
                )
            ) from error


def _markdown_blocks(markdown: str) -> List[str]:
    """Keep heading lines distinct even when an extractor omits a blank line."""
    blocks: List[str] = []
    paragraph: List[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append("\n".join(paragraph).strip())
            paragraph.clear()

    for line in markdown.splitlines():
        if re.match(r"^#{1,6}\s+\S", line):
            flush()
            blocks.append(line.strip())
        elif line.strip():
            paragraph.append(line.rstrip())
        else:
            flush()
    flush()
    return [block for block in blocks if block]


def _active_outline_path(outline: Sequence[OutlineEntry], page: int) -> List[str]:
    path: List[str] = []
    for entry in outline:
        if entry.page > page:
            continue
        level = max(1, entry.level)
        path = path[: level - 1]
        while len(path) < level - 1:
            path.append("Untitled")
        path.append(entry.title)
    return path


def _looks_unusable(page: ExtractedPage) -> bool:
    text = page.markdown.strip()
    if len(text) < 40:
        return True
    replacement_ratio = text.count("\ufffd") / max(1, len(text))
    return replacement_ratio > 0.01


class PDFIngestor:
    """Converts a PDF into traceable blocks while hiding parser routing."""

    def __init__(
        self,
        primary: Optional[PDFExtractionBackend] = None,
        compatibility: Optional[PDFExtractionBackend] = None,
        page_fallback: Optional[PageFallback] = None,
    ):
        self.primary = primary or PyMuPDF4LLMBackend()
        self.compatibility = compatibility or PopplerBackend()
        self.page_fallback = page_fallback

    def _extract(self, path: Path) -> PDFExtraction:
        try:
            return self.primary.extract(path)
        except PDFProcessingError as primary_error:
            extraction = self.compatibility.extract(path)
            extraction.warnings.insert(
                0, "Primary parser unavailable or failed: {0}".format(primary_error)
            )
            return extraction

    def convert(
        self, source: SourceCandidate, path: Path, source_hash: str
    ) -> Tuple[StructuredDocument, str]:
        extraction = self._extract(path)
        warnings = list(extraction.warnings)
        blocks: List[DocumentBlock] = []
        markdown: List[str] = []
        block_number = 0
        fallback_pages: List[int] = []

        for page in sorted(extraction.pages, key=lambda item: item.number):
            page_text = page.markdown.strip()
            confidence = page.confidence
            if _looks_unusable(page) and self.page_fallback is not None:
                try:
                    recovered = self.page_fallback.extract_page(path, page.number).strip()
                except PDFProcessingError as error:
                    recovered = ""
                    warnings.append(str(error))
                if recovered:
                    page_text = recovered
                    confidence = 0.8
                    fallback_pages.append(page.number)
                    warnings.append(
                        "Page {0} required OCR/layout fallback via {1}".format(
                            page.number, self.page_fallback.provider_id
                        )
                    )
            if not page_text:
                warnings.append("No text extracted from page {0}".format(page.number))
                continue
            for warning in page.warnings:
                warnings.append("Page {0}: {1}".format(page.number, warning))

            hierarchy = _active_outline_path(extraction.outline, page.number)
            markdown.append("<!-- source-page: {0} -->".format(page.number))
            for value in _markdown_blocks(page_text):
                block_number += 1
                heading_match = re.match(r"^(#{1,6})\s+(.+)$", value.splitlines()[0])
                kind = "heading" if heading_match else "paragraph"
                block_path = list(hierarchy)
                text = value
                if heading_match:
                    level = len(heading_match.group(1))
                    title = heading_match.group(2).strip()
                    text = title
                    if not extraction.outline:
                        block_path = block_path[: level - 1] + [title]
                        hierarchy = list(block_path)
                section = block_path[-1] if block_path else None
                blocks.append(
                    DocumentBlock(
                        block_id="b{0:05d}".format(block_number),
                        kind=kind,
                        text=text,
                        location="page:{0}".format(page.number),
                        section=section,
                        page=page.number,
                        page_end=page.number,
                        heading_path=block_path,
                        confidence=confidence,
                    )
                )
                markdown.append(value)

        metadata = dict(extraction.metadata)
        metadata.update(
            {
                "extractor": extraction.backend_id,
                "page_count_extracted": str(len(extraction.pages)),
                "outline_entry_count": len(extraction.outline),
                "fallback_provider": getattr(self.page_fallback, "provider_id", None),
                "ocr_provider": getattr(self.page_fallback, "provider_id", None),
                "fallback_pages": fallback_pages,
            }
        )
        document = StructuredDocument(
            source_id=source.source_id,
            title=source.title,
            source_type=source.source_type,
            source_hash=source_hash,
            metadata=metadata,
            blocks=blocks,
            warnings=list(dict.fromkeys(warnings)),
        )
        return document, "\n\n".join(markdown).rstrip() + "\n"
