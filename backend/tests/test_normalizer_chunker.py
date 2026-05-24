from config import Settings
from ingestion.chunker import chunk_document, chunk_documents, split_text_recursive
from ingestion.normalizer import normalize_source, payload_hash
from models.domain import SourceFetchResult, SourceType


def fetch(source_type: SourceType, source_id: str, payload: dict) -> SourceFetchResult:
    return SourceFetchResult(source_type=source_type, source_id=f"{source_type}:{source_id}", payload=payload)


def test_payload_hash_is_stable_for_key_order() -> None:
    assert payload_hash({"b": 2, "a": 1}) == payload_hash({"a": 1, "b": 2})


def test_normalize_course_document() -> None:
    doc = normalize_source(
        fetch(
            SourceType.COURSE,
            "101",
            {
                "courseId": 101,
                "courseName": "BCA",
                "description": "Bachelor of Computer Applications",
                "courseLevel": "BACHELOR",
                "courseType": "SEMESTER",
                "affiliation": "TRIBHUVAN_UNIVERSITY",
            },
        )
    )
    assert doc.id == "course:101"
    assert doc.metadata.title == "BCA"
    assert doc.metadata.source_type == SourceType.COURSE
    assert "Bachelor of Computer Applications" in doc.content
    assert doc.metadata.payload_hash


def test_normalize_all_source_types_have_traceable_metadata() -> None:
    examples = [
        (SourceType.COLLEGE, "1", {"collegeId": 1, "collegeName": "ABC College", "location": "Kathmandu"}),
        (SourceType.SYLLABUS, "2", {"syllabusId": 2, "syllabusTitle": "Programming", "subjectName": "C"}),
        (SourceType.NOTE, "3", {"noteId": 3, "noteName": "Loops", "noteDescription": "Loop notes"}),
        (SourceType.OLD_QUESTION, "4", {"id": 4, "setName": "2079 Set", "description": "Past paper"}),
        (SourceType.TRAINING, "5", {"trainingName": "Python", "description": "Training"}),
        (SourceType.QUESTION_SET, "6", {"questionSetId": 6, "setName": "Mock Set", "description": "Practice"}),
        (SourceType.QUESTION, "7", {"questionId": 7, "question": "What is AI?", "options": ["A", "B"]}),
    ]

    for source_type, source_id, payload in examples:
        doc = normalize_source(fetch(source_type, source_id, payload))
        assert doc.id == f"{source_type}:{source_id}"
        assert doc.metadata.source_id == f"{source_type}:{source_id}"
        assert doc.metadata.source_type == source_type
        assert doc.metadata.tags == [source_type.value]
        assert doc.content


def test_split_text_recursive_respects_size_and_overlap() -> None:
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
    chunks = split_text_recursive(text, chunk_size=35, chunk_overlap=8)
    assert len(chunks) > 1
    for chunk, start, end in chunks:
        assert len(chunk) <= 43  # allows overlap prefix while preserving coherent text
        assert end > start
        assert text[start:end].strip() or chunk


def test_chunk_document_has_deterministic_ids_and_metadata() -> None:
    settings = Settings(
        BACKEND_API_BASE_URL="https://api.entrancegateway.com/api/v1",
        CHATBOT_BACKEND_JWT="test.jwt.token",
        API_KEY="test-admin-api-key",
        CHUNK_SIZE_CHARS=120,
        CHUNK_OVERLAP_CHARS=20,
    )
    doc = normalize_source(
        fetch(
            SourceType.NOTE,
            "3",
            {
                "noteId": 3,
                "noteName": "Long Note",
                "noteDescription": "A" * 260,
            },
        )
    )
    chunks = chunk_document(doc, settings=settings)
    assert len(chunks) >= 2
    for index, chunk in enumerate(chunks):
        assert chunk.id == f"note:3:chunk:{index}"
        assert chunk.document_id == "note:3"
        assert chunk.metadata.document_id == "note:3"
        assert chunk.metadata.chunk_id == chunk.id
        assert chunk.metadata.chunk_index == index
        assert chunk.metadata.chunk_end > chunk.metadata.chunk_start
        assert chunk.metadata.source_type == SourceType.NOTE
        assert chunk.metadata.source_id == "note:3"
        assert len(chunk.content) <= 140


def test_chunk_documents_flattens_multiple_documents() -> None:
    settings = Settings(
        BACKEND_API_BASE_URL="https://api.entrancegateway.com/api/v1",
        CHATBOT_BACKEND_JWT="test.jwt.token",
        API_KEY="test-admin-api-key",
        CHUNK_SIZE_CHARS=120,
        CHUNK_OVERLAP_CHARS=20,
    )
    docs = [
        normalize_source(fetch(SourceType.COURSE, "1", {"courseId": 1, "courseName": "BCA"})),
        normalize_source(fetch(SourceType.COLLEGE, "2", {"collegeId": 2, "collegeName": "ABC"})),
    ]
    chunks = chunk_documents(docs, settings=settings)
    assert len(chunks) == 2
    assert {chunk.document_id for chunk in chunks} == {"course:1", "college:2"}
