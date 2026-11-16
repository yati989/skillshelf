"""A small transparent lexical retrieval index for the first vertical slice."""

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence

from .models import StructuredDocument


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")


def tokenize(value: str) -> List[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(value)]


def _location(blocks: Sequence[Any]) -> str:
    pages = [block.page for block in blocks if block.page is not None]
    if pages:
        start, end = min(pages), max(pages)
        return "page:{0}".format(start) if start == end else "pages:{0}-{1}".format(start, end)
    if len(blocks) == 1:
        return blocks[0].location
    return "{0}..{1}".format(blocks[0].location, blocks[-1].location)


def _split_block_text(text: str, maximum_tokens: int) -> List[str]:
    words = text.split()
    if len(tokenize(text)) <= maximum_tokens:
        return [text]
    parts: List[str] = []
    current: List[str] = []
    token_total = 0
    for word in words:
        count = max(1, len(tokenize(word)))
        if current and token_total + count > maximum_tokens:
            parts.append(" ".join(current))
            current, token_total = [], 0
        current.append(word)
        token_total += count
    if current:
        parts.append(" ".join(current))
    return parts


def build_retrieval_chunks(
    documents: Iterable[StructuredDocument], maximum_tokens: int = 700
) -> List[Dict[str, Any]]:
    """Build coherent, hierarchy-aware chunks with stable source provenance."""
    chunks: List[Dict[str, Any]] = []
    for document in documents:
        source_chunks: List[Dict[str, Any]] = []
        pending: List[Any] = []
        pending_text: List[str] = []
        pending_tokens = 0
        pending_path: Optional[List[str]] = None

        def flush() -> None:
            nonlocal pending, pending_text, pending_tokens, pending_path
            if not pending_text:
                return
            number = len(source_chunks) + 1
            text = "\n\n".join(pending_text)
            path = list(pending_path or [])
            source_chunks.append(
                {
                    "chunk_id": "{0}:c{1:05d}".format(document.source_id, number),
                    "source_id": document.source_id,
                    "source_hash": document.source_hash,
                    "location": _location(pending),
                    "section": path[-1] if path else pending[-1].section,
                    "heading_path": path,
                    "page_start": min(
                        (block.page for block in pending if block.page is not None),
                        default=None,
                    ),
                    "page_end": max(
                        ((block.page_end or block.page) for block in pending if block.page is not None),
                        default=None,
                    ),
                    "block_ids": [block.block_id for block in pending],
                    "text": text,
                    "token_count": len(tokenize(text)),
                }
            )
            pending, pending_text, pending_tokens, pending_path = [], [], 0, None

        for block in document.blocks:
            if not block.text.strip():
                continue
            block_path = list(block.heading_path)
            pending_has_body = any(item.kind != "heading" for item in pending)
            if block.kind == "heading":
                if pending_has_body:
                    flush()
                pending_path = block_path
            else:
                group_changed = bool(pending) and block_path != (pending_path or [])
                if group_changed and pending_has_body:
                    flush()
                elif pending and not pending_has_body:
                    pending_path = block_path
            for part in _split_block_text(block.text.strip(), maximum_tokens):
                part_tokens = len(tokenize(part))
                if pending and pending_tokens + part_tokens > maximum_tokens:
                    flush()
                if pending_path is None:
                    pending_path = block_path
                pending.append(block)
                pending_text.append(part)
                pending_tokens += part_tokens
        flush()

        for index, chunk in enumerate(source_chunks):
            chunk["previous_chunk_id"] = (
                source_chunks[index - 1]["chunk_id"] if index else None
            )
            chunk["next_chunk_id"] = (
                source_chunks[index + 1]["chunk_id"]
                if index + 1 < len(source_chunks)
                else None
            )
        chunks.extend(source_chunks)
    return chunks


def _with_context(
    index: Dict[str, Any],
    results: List[Dict[str, Any]],
    token_budget: int,
    maximum_chunks: int,
) -> List[Dict[str, Any]]:
    by_id = {chunk["chunk_id"]: chunk for chunk in index.get("chunks", [])}
    for result in results:
        selected = [result["chunk_id"]]
        total = result.get("token_count", 0)
        anchor_path = result.get("heading_path") or []
        anchor_chapter = anchor_path[0] if anchor_path else None
        previous = result.get("previous_chunk_id")
        following = result.get("next_chunk_id")
        while (previous or following) and len(selected) < maximum_chunks:
            changed = False
            for candidate_id, direction in ((previous, "previous"), (following, "next")):
                if not candidate_id or len(selected) >= maximum_chunks:
                    continue
                candidate = by_id[candidate_id]
                candidate_path = candidate.get("heading_path") or []
                candidate_chapter = candidate_path[0] if candidate_path else None
                if candidate_chapter != anchor_chapter:
                    if direction == "previous":
                        previous = None
                    else:
                        following = None
                    continue
                if total + candidate["token_count"] > token_budget:
                    if direction == "previous":
                        previous = None
                    else:
                        following = None
                    continue
                if direction == "previous":
                    selected.insert(0, candidate_id)
                    previous = candidate.get("previous_chunk_id")
                else:
                    selected.append(candidate_id)
                    following = candidate.get("next_chunk_id")
                total += candidate["token_count"]
                changed = True
            if not changed:
                break
        result["context_chunk_ids"] = selected
        result["context_token_count"] = total
        result["context_text"] = "\n\n".join(by_id[item]["text"] for item in selected)
    return results


class LexicalIndex:
    """Serializable BM25-like index whose matches retain exact source locations."""

    @staticmethod
    def build(documents: Iterable[StructuredDocument]) -> Dict[str, Any]:
        chunks = build_retrieval_chunks(documents)
        document_frequency: Counter = Counter()
        for chunk in chunks:
            counts = Counter(tokenize(chunk["text"]))
            chunk["token_counts"] = dict(counts)
            document_frequency.update(counts.keys())
        average_length = (
            sum(chunk["token_count"] for chunk in chunks) / len(chunks) if chunks else 0.0
        )
        return {
            "version": 2,
            "chunk_count": len(chunks),
            "average_length": average_length,
            "document_frequency": dict(document_frequency),
            "chunks": chunks,
        }

    @staticmethod
    def search(
        index: Dict[str, Any],
        query: str,
        limit: int = 5,
        context_token_budget: int = 1400,
        context_chunk_limit: int = 3,
    ) -> List[Dict[str, Any]]:
        query_tokens = list(dict.fromkeys(tokenize(query)))
        if not query_tokens or not index.get("chunks"):
            return []
        total = index["chunk_count"]
        average_length = index.get("average_length") or 1.0
        frequencies = index.get("document_frequency", {})
        scored: List[Dict[str, Any]] = []
        for chunk in index["chunks"]:
            score = 0.0
            length = chunk["token_count"] or 1
            for token in query_tokens:
                term_frequency = chunk["token_counts"].get(token, 0)
                if not term_frequency:
                    continue
                containing = frequencies.get(token, 0)
                inverse_frequency = math.log(1 + (total - containing + 0.5) / (containing + 0.5))
                denominator = term_frequency + 1.2 * (0.25 + 0.75 * length / average_length)
                score += inverse_frequency * (term_frequency * 2.2 / denominator)
            if score:
                result = {key: value for key, value in chunk.items() if key != "token_counts"}
                result["score"] = round(score, 6)
                scored.append(result)
        scored.sort(key=lambda item: (-item["score"], item["chunk_id"]))
        return _with_context(
            index, scored[:limit], context_token_budget, context_chunk_limit
        )


class EmbeddingProvider(Protocol):
    """Provider seam; implementations may be local or remote."""

    @property
    def model_id(self) -> str:
        ...

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        ...


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions do not match")
    numerator = sum(a * b for a, b in zip(left, right))
    left_length = math.sqrt(sum(value * value for value in left))
    right_length = math.sqrt(sum(value * value for value in right))
    if not left_length or not right_length:
        return 0.0
    return numerator / (left_length * right_length)


class VectorIndex:
    @staticmethod
    def build(
        documents: Iterable[StructuredDocument], provider: EmbeddingProvider
    ) -> Dict[str, Any]:
        chunks = build_retrieval_chunks(documents)
        vectors = provider.embed([chunk["text"] for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding provider returned the wrong vector count")
        dimensions = len(vectors[0]) if vectors else 0
        if any(len(vector) != dimensions for vector in vectors):
            raise ValueError("Embedding provider returned inconsistent dimensions")
        for chunk, vector in zip(chunks, vectors):
            chunk["vector"] = vector
        return {
            "version": 2,
            "model_id": provider.model_id,
            "dimensions": dimensions,
            "chunks": chunks,
        }

    @staticmethod
    def search(
        index: Dict[str, Any], query: str, provider: EmbeddingProvider, limit: int = 5
    ) -> List[Dict[str, Any]]:
        if provider.model_id != index.get("model_id"):
            raise ValueError("Query embedding model does not match the stored index")
        query_vectors = provider.embed([query])
        if len(query_vectors) != 1:
            raise ValueError("Embedding provider did not return one query vector")
        query_vector = query_vectors[0]
        scored: List[Dict[str, Any]] = []
        for chunk in index.get("chunks", []):
            result = {key: value for key, value in chunk.items() if key != "vector"}
            result["score"] = round(_cosine(query_vector, chunk["vector"]), 6)
            scored.append(result)
        scored.sort(key=lambda item: (-item["score"], item["chunk_id"]))
        return scored[:limit]


class HybridRetriever:
    """Combines transparent lexical and optional semantic rankings."""

    @staticmethod
    def search(
        lexical_index: Dict[str, Any],
        vector_index: Dict[str, Any],
        query: str,
        provider: EmbeddingProvider,
        limit: int = 5,
        lexical_weight: float = 0.55,
    ) -> List[Dict[str, Any]]:
        if not 0.0 <= lexical_weight <= 1.0:
            raise ValueError("lexical_weight must fall between zero and one")
        candidate_limit = max(limit * 4, 20)
        lexical = LexicalIndex.search(lexical_index, query, candidate_limit)
        semantic = VectorIndex.search(vector_index, query, provider, candidate_limit)
        lexical_max = max((item["score"] for item in lexical), default=1.0) or 1.0
        combined: Dict[str, Dict[str, Any]] = {}
        for item in lexical:
            entry = dict(item)
            entry["lexical_score"] = item["score"] / lexical_max
            entry["semantic_score"] = 0.0
            combined[item["chunk_id"]] = entry
        for item in semantic:
            entry = combined.setdefault(item["chunk_id"], dict(item))
            entry.setdefault("lexical_score", 0.0)
            entry["semantic_score"] = (item["score"] + 1.0) / 2.0
        for entry in combined.values():
            entry["score"] = round(
                lexical_weight * entry["lexical_score"]
                + (1.0 - lexical_weight) * entry["semantic_score"],
                6,
            )
        ranked = sorted(
            combined.values(), key=lambda item: (-item["score"], item["chunk_id"])
        )
        return ranked[:limit]
