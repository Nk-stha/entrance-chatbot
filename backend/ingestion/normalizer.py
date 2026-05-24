from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from models.domain import DocumentMetadata, NormalizedDocument, SourceFetchResult, SourceType


def payload_hash(payload: dict[str, Any]) -> str:
    """Create a stable hash for change detection."""

    serialized = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def first_present(payload: dict[str, Any], keys: Iterable[str], default: str = "Untitled") -> str:
    """Return the first non-empty string-like value for the provided keys."""

    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def append_field(lines: list[str], label: str, value: Any) -> None:
    """Append a readable field if value is present."""

    if value is None or value == "":
        return
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if item is not None and str(item).strip())
    if isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False, default=str)
    text = str(value).strip()
    if text:
        lines.append(f"{label}: {text}.")


def build_content(payload: dict[str, Any], field_map: list[tuple[str, str]]) -> str:
    """Build concise human-readable content instead of embedding raw JSON."""

    lines: list[str] = []
    for label, key in field_map:
        append_field(lines, label, payload.get(key))
    return "\n".join(lines).strip()


FIELD_MAPS: dict[SourceType, list[tuple[str, str]]] = {
    SourceType.COURSE: [
        ("Course", "courseName"),
        ("Description", "description"),
        ("Level", "courseLevel"),
        ("Type", "courseType"),
        ("Affiliation", "affiliation"),
        ("Available colleges", "collegeResponses"),
    ],
    SourceType.COLLEGE: [
        ("College", "collegeName"),
        ("Location", "location"),
        ("Affiliation", "affiliation"),
        ("Website", "website"),
        ("Contact", "contact"),
        ("Email", "email"),
        ("Description", "description"),
        ("Established year", "establishedYear"),
        ("College type", "collegeType"),
        ("Priority", "priority"),
        ("Courses", "courses"),
    ],
    SourceType.SYLLABUS: [
        ("Syllabus", "syllabusTitle"),
        ("Subject", "subjectName"),
        ("Course", "courseName"),
        ("Course code", "courseCode"),
        ("Credit hours", "creditHours"),
        ("Lecture hours", "lectureHours"),
        ("Practical hours", "practicalHours"),
        ("Semester", "semester"),
        ("Year", "year"),
        ("File", "syllabusFile"),
    ],
    SourceType.NOTE: [
        ("Note", "noteName"),
        ("Subject", "subject"),
        ("Subject code", "subjectCode"),
        ("Description", "noteDescription"),
        ("Course ID", "courseId"),
        ("Syllabus ID", "syllabusId"),
    ],
    SourceType.OLD_QUESTION: [
        ("Old question set", "setName"),
        ("Description", "description"),
        ("Year", "year"),
        ("Subject", "subject"),
        ("Course", "courseName"),
        ("PDF", "pdfFilePath"),
    ],
    SourceType.TRAINING: [
        ("Training", "trainingName"),
        ("Description", "description"),
        ("Start date", "startDate"),
        ("End date", "endDate"),
        ("Type", "trainingType"),
        ("Status", "trainingStatus"),
        ("Hours", "trainingHours"),
        ("Location", "location"),
        ("Category", "trainingCategory"),
        ("Cost", "cost"),
        ("Certificate provided", "certificateProvided"),
        ("Materials", "materialsLink"),
        ("Remarks", "remarks"),
    ],
    SourceType.QUESTION_SET: [
        ("Question set", "setName"),
        ("Description", "description"),
        ("Price", "price"),
        ("Course", "courseName"),
        ("Course ID", "courseId"),
    ],
    SourceType.QUESTION: [
        ("Question", "question"),
        ("Options", "options"),
        ("Correct answer index", "correctAnswerIndex"),
        ("Marks", "marks"),
        ("Category", "categoryName"),
        ("Question set", "questionSetTitle"),
    ],
}

TITLE_FIELDS: dict[SourceType, tuple[str, ...]] = {
    SourceType.COURSE: ("courseName",),
    SourceType.COLLEGE: ("collegeName",),
    SourceType.SYLLABUS: ("syllabusTitle", "subjectName"),
    SourceType.NOTE: ("noteName",),
    SourceType.OLD_QUESTION: ("setName", "subject"),
    SourceType.TRAINING: ("trainingName",),
    SourceType.QUESTION_SET: ("setName",),
    SourceType.QUESTION: ("questionSetTitle", "question"),
}


def normalize_source(fetch_result: SourceFetchResult) -> NormalizedDocument:
    """Normalize one Java backend API record into a canonical document."""

    payload = fetch_result.payload
    source_type = fetch_result.source_type
    title = first_present(payload, TITLE_FIELDS[source_type])
    content = build_content(payload, FIELD_MAPS[source_type])
    if not content:
        content = title

    metadata = DocumentMetadata(
        source_type=source_type,
        source_id=fetch_result.source_id,
        title=title,
        category=source_type.value,
        tags=[source_type.value],
        url=_extract_url(payload),
        payload_hash=payload_hash(payload),
    )
    return NormalizedDocument(
        id=fetch_result.source_id,
        content=content,
        metadata=metadata,
        raw=payload,
    )


def normalize_sources(fetch_results: Iterable[SourceFetchResult]) -> list[NormalizedDocument]:
    """Normalize multiple Java backend source records."""

    return [normalize_source(result) for result in fetch_results]


def _extract_url(payload: dict[str, Any]) -> str | None:
    for key in ("website", "materialsLink", "pdfFilePath", "syllabusFile"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return None
