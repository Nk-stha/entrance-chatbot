# RAG Knowledge Source API Inventory

## Purpose

This document defines the real backend APIs that the RAG chatbot will ingest from.
The chatbot will use these APIs as the **only knowledge source**.

> No web scraping is required or allowed.

---

## Base URLs

### Local development

```http
http://localhost:8080/api/v1
```

### Production

```http
http://api.entrancegateway.com/api/v1
```

---

## Response Shapes

### Common paginated wrapper

Most list endpoints return:

```json
{
  "message": "List message",
  "data": {
    "content": [],
    "pageable": {},
    "totalElements": 0,
    "totalPages": 0,
    "last": true,
    "size": 10,
    "number": 0,
    "sort": {},
    "first": true,
    "numberOfElements": 0,
    "empty": true
  }
}
```

For these endpoints, the ingestion pipeline should read:

```text
response.data.content[]
```

### Direct Spring Page response

Some endpoints return a Spring `Page<T>` directly, without the `ApiResponse` wrapper.
For those endpoints, the ingestion pipeline should read:

```text
response.content[]
```

### Direct list response

Some endpoints return a raw list:

```json
[
  {...},
  {...}
]
```

For those endpoints, the ingestion pipeline should read the response body directly.

---

## Common Pagination Parameters

| Parameter | Type | Default | Notes |
|---|---:|---:|---|
| `page` | integer | `0` | Zero-based page index |
| `size` | integer | `10` | Page size |
| `sortBy` | string | endpoint-specific | Invalid values may return `400` |
| `sortDir` | string | `asc` | `asc` or `desc` |

Recommended ingestion defaults:

```text
page=0
size=100
sortDir=asc
```

The ingestion client should continue fetching until:

```text
last == true
```

or until:

```text
number >= totalPages - 1
```

---

## Authentication Notes

Public GET access is explicitly configured for:

- `/api/v1/colleges/**`
- `/api/v1/courses/**`
- `/api/v1/trainings/**`
- `/api/v1/syllabuses/**`

Important caveat:

- The actual syllabus controller path is `/api/v1/syllabus`, singular.
- Security allows `/api/v1/syllabuses/**`, plural.
- So `/api/v1/syllabus` may require authentication unless the security config is corrected.

Likely protected endpoints:

- `/api/v1/notes/**`
- `/api/v1/question-sets/**`
- `/api/v1/questions/**`
- `/api/v1/quiz-attempts/**`
- `/api/v1/old-question-collections/**`

For protected endpoints, the chatbot backend will use a service-account JWT stored in an environment variable:

```env
CHATBOT_BACKEND_JWT=your-service-account-jwt
```

Requests to protected Spring APIs should include:

```http
Authorization: Bearer <value-of-CHATBOT_BACKEND_JWT>
```

Do not use an end-user JWT for ingestion jobs. The chatbot backend should authenticate as a backend service account.

---

## Ingestion Priority

| Priority | Source | Reason |
|---:|---|---|
| 1 | Courses | Core academic knowledge |
| 2 | Colleges | College discovery and metadata |
| 3 | Syllabus | Subject/course structure |
| 4 | Notes | Learning material descriptions |
| 5 | Old Questions | Exam preparation knowledge |
| 6 | Question Sets | Quiz/exam practice metadata |
| 7 | Questions | Question-level practice knowledge |
| 8 | Trainings | Training/program offering knowledge |
| 9 | Quiz Attempts | Usually user-specific; ingest only if needed |

> Quiz attempts are usually user/session data, not public knowledge. Do not ingest them into global RAG unless there is a clear requirement.

---

## Endpoint Inventory

### 1. Syllabus List

```http
GET /api/v1/syllabus?page=0&size=100&sortBy=syllabusTitle&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `syllabusId` | UUID | stable source ID |
| `courseId` | UUID | metadata/filter |
| `syllabusTitle` | string | title/content |
| `syllabusFile` | string | source/file reference |
| `courseCode` | string | metadata/content |
| `creditHours` | number | content |
| `lectureHours` | integer | content |
| `practicalHours` | integer | content |
| `courseName` | string | metadata/content |
| `semester` | integer | metadata/filter |
| `year` | integer | metadata/filter |
| `subjectName` | string | title/content |

Source mapping:

```text
source_type: syllabus
source_id: syllabus:{syllabusId}
title: {syllabusTitle} or {subjectName}
```

---

### 2. Notes List

```http
GET /api/v1/notes?page=0&size=100&sortBy=noteName&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `noteId` | UUID | stable source ID |
| `subject` | string | metadata/content |
| `subjectCode` | string | metadata/content |
| `noteName` | string | title/content |
| `syllabusId` | UUID | metadata/filter |
| `noteDescription` | string | main content |
| `courseId` | UUID | metadata/filter |

Source mapping:

```text
source_type: note
source_id: note:{noteId}
title: {noteName}
```

Additional endpoints, optional for targeted refresh/search:

| Endpoint | Response shape |
|---|---|
| `GET /api/v1/notes/{courseName}/notes` | `ApiResponse.data` list |
| `GET /api/v1/notes/getNotesBy/{courseName}/{semester}` | `ApiResponse.data` list |
| `GET /api/v1/notes/noteName/{noteName}` | `ApiResponse.data` object |
| `GET /api/v1/notes/syllabusTitle/{syllabusTitle}` | `ApiResponse.data` object |

---

### 3. Old Questions List

```http
GET /api/v1/old-question-collections/questions?page=0&size=100&sort=year,desc
```

Wrapper shape:

```text
Spring Page → content[]
```

Optional filters:

| Parameter | Type |
|---|---|
| `courseId` | UUID |
| `syllabusId` | UUID |
| `year` | integer |
| `setName` | string |

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `id` | UUID | stable source ID |
| `setName` | string | title/content |
| `description` | string | main content |
| `year` | integer | metadata/filter |
| `pdfFilePath` | string | source/file reference |
| `syllabusId` | UUID | metadata/filter |
| `subject` | string | metadata/content |
| `courseName` | string | metadata/content |

Source mapping:

```text
source_type: old_question
source_id: old_question:{id}
title: {setName}
```

Additional endpoints:

| Endpoint | Response shape |
|---|---|
| `GET /api/v1/old-question-collections/filter?courseId={courseId}&semester={semester}&year={year}` | Spring Page |
| `GET /api/v1/old-question-collections/syllabus/{syllabusId}` | List |
| `GET /api/v1/old-question-collections/course/{courseId}/semesters` | List<Integer> |
| `GET /api/v1/old-question-collections/course/{courseId}/semester/{semester}/subjects` | List |

---

### 4. Colleges List

```http
GET /api/v1/colleges?page=0&size=100&sortBy=collegeName&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `collegeId` | UUID | stable source ID |
| `collegeName` | string | title/content |
| `location` | string | metadata/content |
| `affiliation` | enum | metadata/filter |
| `website` | string | citation/source info |
| `contact` | string | content |
| `email` | string | content |
| `description` | string | main content |
| `establishedYear` | string | content |
| `collegeType` | enum | metadata/filter |
| `priority` | enum | metadata/filter |
| `courses` | array | nested content/metadata |

Source mapping:

```text
source_type: college
source_id: college:{collegeId}
title: {collegeName}
```

Search endpoint:

```http
GET /api/v1/colleges/search?name={keyword}&page=0&size=10&sortBy=collegeName&sortDir=asc
```

Use search for runtime UI features if needed, not for full ingestion.

---

### 5. Courses List

```http
GET /api/v1/courses?page=0&size=100&sortBy=courseName&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `courseId` | UUID | stable source ID |
| `courseName` | string | title/content |
| `description` | string | main content |
| `collegeId` | UUID | metadata/filter |
| `courseLevel` | enum | metadata/filter |
| `courseType` | enum | metadata/filter |
| `affiliation` | enum | metadata/filter |
| `collegeResponses` | array | nested content/metadata |

Source mapping:

```text
source_type: course
source_id: course:{courseId}
title: {courseName}
```

Filter endpoint:

```http
GET /api/v1/courses/by-affiliation?affiliation={affiliation}&page=0&size=100
```

Use for targeted refresh or runtime filtering if needed.

---

### 6. Trainings List

```http
GET /api/v1/trainings?page=0&size=100&sortBy=trainingStatus&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `trainingName` | string | title/content |
| `description` | string | main content |
| `startDate` | date | metadata/content |
| `endDate` | date | metadata/content |
| `trainingType` | enum | metadata/filter |
| `trainingStatus` | enum | metadata/filter |
| `trainingHours` | integer | content |
| `location` | string | metadata/content |
| `maxParticipants` | integer | content |
| `currentParticipants` | integer | content |
| `trainingCategory` | string | metadata/filter |
| `cost` | number | content |
| `certificateProvided` | boolean | content |
| `materialsLink` | string | citation/source info |
| `remarks` | string | content |

Source mapping:

```text
source_type: training
source_id: training:{trainingName}:{startDate}
title: {trainingName}
```

> If trainings have a hidden stable ID, use that instead of name/date.

---

### 7. Question Sets

```http
GET /api/v1/question-sets?page=0&size=100&sortBy=setName&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `questionSetId` | UUID | stable source ID |
| `setName` | string | title/content |
| `description` | string | main content |
| `price` | number | content |
| `courseId` | UUID | metadata/filter |
| `courseName` | string | metadata/content |

Source mapping:

```text
source_type: question_set
source_id: question_set:{questionSetId}
title: {setName}
```

Additional endpoints:

| Endpoint | Response shape |
|---|---|
| `GET /api/v1/question-sets/free?page=0&size=100&sortBy=categoryName&sortDir=asc` | ApiResponse |
| `GET /api/v1/question-sets/course/{courseId}?page=0&size=100&sortBy=setName&sortDir=asc` | ApiResponse paginated |

---

### 8. Questions

```http
GET /api/v1/questions?page=0&size=100&sortBy=category.categoryName&sortDir=asc
```

Wrapper shape:

```text
ApiResponse → data.content[]
```

Fields:

| Field | Type | RAG usage |
|---|---|---|
| `questionId` | UUID | stable source ID |
| `question` | string | main content |
| `options` | array string | content |
| `correctAnswerIndex` | integer | answer content |
| `marks` | integer | metadata/content |
| `categoryId` | UUID | metadata/filter |
| `categoryName` | string | metadata/filter |
| `questionSetId` | UUID | metadata/filter |
| `questionSetTitle` | string | metadata/content |

Source mapping:

```text
source_type: question
source_id: question:{questionId}
title: {questionSetTitle} question
```

Questions by set:

```http
GET /api/v1/questions/set/{questionSetId}?page=0&size=100&sortBy=question&sortDir=asc
```

---

### 9. Quiz Attempts

```http
GET /api/v1/quiz-attempts?page=0&size=100&sortDir=asc
```

```http
GET /api/v1/quiz-attempts/user
```

Recommendation:

Do **not** ingest quiz attempts into the global RAG knowledge base by default because they are usually user-specific attempt history.

Use only if the chatbot must answer authenticated user-specific performance questions.

---

## No Blog API

No Blog API exists in this codebase.

Searches for `Blog`, `blog`, and `blogs` found no controller, model, service, repository, or route.

Therefore:

```text
source_type: blog
status: unavailable
```

Do not include blogs in ingestion until a real backend endpoint exists.

---

## Normalization Strategy

Each item from each API should become a `NormalizedDocument`:

```json
{
  "source_type": "course",
  "source_id": "course:<courseId>",
  "title": "Course Name",
  "content": "Readable text built from important fields.",
  "metadata": {
    "courseId": "...",
    "courseLevel": "BACHELOR",
    "courseType": "SEMESTER",
    "affiliation": "TRIBHUVAN_UNIVERSITY"
  }
}
```

The `content` field should be human-readable, not raw JSON.

Example course content:

```text
Course: Bachelor of Computer Applications.
Description: ...
Level: BACHELOR.
Type: SEMESTER.
Affiliation: TRIBHUVAN_UNIVERSITY.
Available colleges: ...
```

---

## Incremental Sync Strategy

Incremental sync will be **webhook-driven** from the Java backend.

When data changes in the Java backend, the Java backend should call the chatbot webhook endpoint and include enough information for targeted refresh.

Recommended chatbot endpoint:

```http
POST /api/v1/webhooks/sync
```

Recommended webhook payload:

```json
{
  "event_id": "uuid-or-unique-event-id",
  "event_type": "updated",
  "source_type": "course",
  "source_ids": ["course-uuid-1"],
  "occurred_at": "2026-05-21T16:00:00Z"
}
```

Supported event types:

| Event type | Behavior |
|---|---|
| `created` | Fetch the changed record, normalize, chunk, embed, and upsert into ChromaDB |
| `updated` | Delete old chunks for the record, then fetch/re-index the latest record |
| `deleted` | Delete chunks for the record from ChromaDB |
| `bulk_refresh` | Refresh all records for the given `source_type` |

Security:

- Use `WEBHOOK_SECRET` to sign or validate webhook requests.
- Store processed `event_id` values in Redis to prevent duplicate processing.
- Reject webhook events with unknown `source_type`.

Fallback full sync:

- Keep a manual/admin full sync endpoint for recovery.
- Full sync can still use content hashes to avoid unnecessary re-embedding.

Recommended deterministic chunk ID:

```text
{source_type}:{source_primary_id}:chunk:{chunk_index}
```

Examples:

```text
course:2f3a...:chunk:0
college:9a1b...:chunk:0
question:77c1...:chunk:0
```

---

## Enum Values

| Enum | Values |
|---|---|
| `Affiliation` | `TRIBHUVAN_UNIVERSITY`, `POKHARA_UNIVERSITY`, `KATHMANDU_UNIVERSITY`, `PURWANCHAL_UNIVERSITY`, `MID_WESTERN_UNIVERSITY`, `FAR_WESTERN_UNIVERSITY`, `LUMBINI_UNIVERSITY`, `CAMPUS_AFFILIATED_TO_FOREIGN_UNIVERSITY` |
| `CollegeType` | `PRIVATE`, `COMMUNITY`, `GOVERNMENT` |
| `CourseLevel` | `PLUS_TWO`, `BACHELOR`, `MASTER`, `PHD`, `DIPLOMA`, `M_PHIL` |
| `CourseType` | `SEMESTER`, `ANNUAL` |
| `Priority` | `HIGH`, `MEDIUM`, `LOW` |
| `TrainingStatus` | `UPCOMING`, `FLASH_SALE`, `ONGOING`, `COMPLETED`, `CANCELLED`, `POSTPONED`, `COMING_SOON`, `REGISTRATION_OPEN`, `REGISTRATION_CLOSED`, `SOLD_OUT` |
| `TrainingType` | `REMOTE`, `ON_SITE`, `HYBRID` |

---

## Implementation Notes for BackendAPIClient

The API client should support multiple response extractors:

```python
def extract_items(response_json: dict | list, shape: str) -> list[dict]:
    if shape == "api_page":
        return response_json["data"]["content"]
    if shape == "spring_page":
        return response_json["content"]
    if shape == "api_list":
        return response_json["data"]
    if shape == "direct_list":
        return response_json
    if shape == "api_object":
        return [response_json["data"]]
    raise ValueError(f"Unsupported response shape: {shape}")
```

Recommended endpoint config shape:

```python
SOURCE_ENDPOINTS = [
    {
        "source_type": "course",
        "path": "/courses",
        "response_shape": "api_page",
        "id_field": "courseId",
        "title_field": "courseName",
        "default_sort_by": "courseName",
        "requires_auth": False,
    },
    {
        "source_type": "note",
        "path": "/notes",
        "response_shape": "api_page",
        "id_field": "noteId",
        "title_field": "noteName",
        "default_sort_by": "noteName",
        "requires_auth": True,
    },
]
```
