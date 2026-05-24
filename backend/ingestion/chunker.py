from __future__ import annotations

from collections.abc import Iterable

from config import Settings, get_settings
from models.domain import ChunkMetadata, DocumentChunk, NormalizedDocument


SEPARATORS = ("\n\n", "\n", ". ", " ", "")


def split_text_recursive(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[tuple[str, int, int]]:
    """Split text recursively with deterministic offsets.

    This implements the same separator idea as LangChain's
    RecursiveCharacterTextSplitter while keeping the backend lightweight and
    avoiding another runtime dependency in the VPS container.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    clean_text = text.strip()
    if not clean_text:
        return []

    pieces = _recursive_split(clean_text, chunk_size, SEPARATORS)
    chunks: list[tuple[str, int, int]] = []
    current = ""
    search_from = 0

    for piece in pieces:
        candidate = piece if not current else f"{current} {piece}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            start = clean_text.find(current, search_from)
            if start < 0:
                start = search_from
            end = start + len(current)
            chunks.append((current, start, end))
            search_from = max(start, end - chunk_overlap)
            overlap_text = clean_text[search_from:end].strip()
            if overlap_text and len(overlap_text) + 1 + len(piece) > chunk_size + chunk_overlap:
                max_overlap = max(0, chunk_size + chunk_overlap - len(piece) - 1)
                overlap_text = overlap_text[-max_overlap:].strip() if max_overlap else ""
            current = f"{overlap_text} {piece}".strip() if overlap_text else piece
        else:
            current = piece

    if current:
        start = clean_text.find(current, search_from)
        if start < 0:
            start = search_from
        end = min(start + len(current), len(clean_text))
        chunks.append((current, start, end))

    return [(chunk, start, end) for chunk, start, end in chunks if chunk.strip() and end > start]


def _recursive_split(text: str, chunk_size: int, separators: tuple[str, ...]) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    separator = separators[0]
    remaining = separators[1:]

    if separator == "":
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]

    parts = text.split(separator)
    if len(parts) == 1:
        return _recursive_split(text, chunk_size, remaining)

    output: list[str] = []
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if len(stripped) <= chunk_size:
            output.append(stripped)
        else:
            output.extend(_recursive_split(stripped, chunk_size, remaining))
    return output


def chunk_document(
    document: NormalizedDocument,
    *,
    settings: Settings | None = None,
) -> list[DocumentChunk]:
    """Chunk one normalized document with deterministic IDs and metadata."""

    cfg = settings or get_settings()
    split_chunks = split_text_recursive(
        document.content,
        chunk_size=cfg.chunk_size_chars,
        chunk_overlap=cfg.chunk_overlap_chars,
    )

    chunks: list[DocumentChunk] = []
    for index, (content, start, end) in enumerate(split_chunks):
        chunk_id = f"{document.id}:chunk:{index}"
        metadata = ChunkMetadata(
            **document.metadata.model_dump(),
            document_id=document.id,
            chunk_id=chunk_id,
            chunk_index=index,
            chunk_start=start,
            chunk_end=end,
        )
        chunks.append(
            DocumentChunk(
                id=chunk_id,
                document_id=document.id,
                content=content,
                metadata=metadata,
            )
        )
    return chunks


def chunk_documents(
    documents: Iterable[NormalizedDocument],
    *,
    settings: Settings | None = None,
) -> list[DocumentChunk]:
    """Chunk multiple normalized documents."""

    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, settings=settings))
    return chunks
