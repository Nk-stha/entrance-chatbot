# Java Backend Integration Guide for Chatbot Admin, Webhook, and Monitoring APIs

This guide explains **how**, **when**, and **why** the Java/Spring Boot backend should integrate with the Entrance Gateway RAG chatbot operational APIs.

The chatbot backend is responsible for:

```text
fetching Java backend data
normalizing documents
chunking text
creating embeddings with Ollama
storing vectors in ChromaDB
serving chat responses from stored knowledge
```

The Java backend should call these APIs only for **data synchronization and monitoring**, not for normal student chat messages.

---

## 1. Base Configuration

### Chatbot Backend Base URL

Local development:

```properties
chatbot.base-url=http://localhost:8002/api/v1
```

Docker/internal network example:

```properties
chatbot.base-url=http://entrance-chatbot-backend:8000/api/v1
```

Production example:

```properties
chatbot.base-url=https://chatbot.your-domain.com/api/v1
```

### Admin API Key

The chatbot backend protects admin and webhook APIs with:

```http
X-API-Key: <API_KEY>
```

In the chatbot project, this value comes from:

```text
API_KEY=...
```

In the Java backend, store the same value securely:

```properties
chatbot.api-key=${CHATBOT_API_KEY}
```

> [!CAUTION]
> Do not hardcode the API key in Java code. Use environment variables or a secret manager.

---

## 2. API Summary

| API | Method | Called By | When To Use | Protected |
| :--- | :--- | :--- | :--- | :--- |
| `/admin/refresh` | `POST` | Admin tool / deployment job | Full rebuild of ChromaDB from all source APIs | Yes |
| `/admin/sync` | `POST` | Admin tool / Java backend service | Manual targeted sync for one source type or source ID | Yes |
| `/admin/stats` | `GET` | Admin dashboard / monitoring | Check ChromaDB collection name and stored chunk count | Yes |
| `/webhooks/sync` | `POST` | Java backend event hooks | Automatic incremental sync after create/update/delete | Yes |
| `/metrics` | `GET` | Prometheus / uptime monitor | Check chatbot service metric output | No |

---

# 3. `POST /api/v1/admin/refresh`

## Purpose

Triggers a **full ingestion refresh**.

The chatbot will fetch every configured source type from the Java backend and rebuild/update ChromaDB.

Flow:

```text
Java/backend APIs
→ chatbot full sync
→ normalize
→ chunk
→ embed
→ upsert into ChromaDB
```

## When To Use

Use this endpoint:

- after initial deployment
- after clearing ChromaDB
- after changing normalizer/chunker/embedder logic
- after changing a large amount of old data
- during manual admin maintenance
- after migration/import scripts

Do **not** call it after every single create/update event. Use `/webhooks/sync` for that.

## Request

```http
POST /api/v1/admin/refresh
X-API-Key: <API_KEY>
```

No request body is required.

## Curl

```bash
CHATBOT_BASE_URL="http://localhost:8002/api/v1"
CHATBOT_API_KEY="replace-with-api-key"

curl -X POST "${CHATBOT_BASE_URL}/admin/refresh" \
  -H "X-API-Key: ${CHATBOT_API_KEY}"
```

## Java WebClient Example

```java
@Service
public class ChatbotAdminClient {

    private final WebClient webClient;
    private final String apiKey;

    public ChatbotAdminClient(
            WebClient.Builder builder,
            @Value("${chatbot.base-url}") String baseUrl,
            @Value("${chatbot.api-key}") String apiKey
    ) {
        this.webClient = builder.baseUrl(baseUrl).build();
        this.apiKey = apiKey;
    }

    public Mono<String> refreshAll() {
        return webClient.post()
                .uri("/admin/refresh")
                .header("X-API-Key", apiKey)
                .retrieve()
                .bodyToMono(String.class);
    }
}
```

## Expected Response

```json
{
  "success": true,
  "report": {
    "fetched_count": 5,
    "normalized_count": 5,
    "chunk_count": 5,
    "embedded_count": 5,
    "upserted_count": 5,
    "skipped_count": 0,
    "errors": []
  }
}
```

---

# 4. `POST /api/v1/admin/sync`

## Purpose

Triggers a **targeted sync** for:

```text
one source type
or
one specific source ID
```

This is useful when an admin wants to manually repair or refresh a specific part of chatbot knowledge.

## Supported `source_type` Values

Current accepted values from chatbot code:

```text
course
college
syllabus
note
old_question
training
question_set
question
```

## When To Use

Use this endpoint:

- when an admin clicks “resync this course”
- when only trainings should be refreshed
- when a specific source failed ingestion
- when debugging one source type
- when a scheduled job wants to refresh one category

For automatic create/update/delete events from Java entities, prefer `/webhooks/sync`.

## Request: Sync One Source Type

```json
{
  "source_type": "training"
}
```

## Request: Sync One Source ID

```json
{
  "source_type": "course",
  "source_id": "course:8"
}
```

## Curl: Sync Trainings

```bash
CHATBOT_BASE_URL="http://localhost:8002/api/v1"
CHATBOT_API_KEY="replace-with-api-key"

curl -X POST "${CHATBOT_BASE_URL}/admin/sync" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${CHATBOT_API_KEY}" \
  -d '{
    "source_type": "training"
  }'
```

## Curl: Sync One Course

```bash
curl -X POST "${CHATBOT_BASE_URL}/admin/sync" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${CHATBOT_API_KEY}" \
  -d '{
    "source_type": "course",
    "source_id": "course:8"
  }'
```

## Java DTO

```java
public record ChatbotSyncRequest(
        String source_type,
        String source_id
) {}
```

For source-type-only sync, pass `null` for `source_id`.

## Java WebClient Example

```java
public Mono<String> syncSource(String sourceType, @Nullable String sourceId) {
    ChatbotSyncRequest request = new ChatbotSyncRequest(sourceType, sourceId);

    return webClient.post()
            .uri("/admin/sync")
            .header("Content-Type", "application/json")
            .header("X-API-Key", apiKey)
            .bodyValue(request)
            .retrieve()
            .bodyToMono(String.class);
}
```

---

# 5. `GET /api/v1/admin/stats`

## Purpose

Returns ChromaDB collection status.

Use this to verify whether the chatbot has stored knowledge.

## When To Use

Use this endpoint:

- in an admin dashboard
- after full refresh
- after sync/webhook events
- in deployment smoke tests
- in monitoring checks that require authentication

## Request

```http
GET /api/v1/admin/stats
X-API-Key: <API_KEY>
```

## Curl

```bash
curl -H "X-API-Key: ${CHATBOT_API_KEY}" \
  "${CHATBOT_BASE_URL}/admin/stats"
```

## Example Response

```json
{
  "collection": "entrance_knowledge",
  "count": 5
}
```

## Java WebClient Example

```java
public Mono<String> getStats() {
    return webClient.get()
            .uri("/admin/stats")
            .header("X-API-Key", apiKey)
            .retrieve()
            .bodyToMono(String.class);
}
```

---

# 6. `POST /api/v1/webhooks/sync`

## Purpose

This is the **recommended API for Java backend integration**.

The Java backend should call this endpoint whenever source data changes.

Examples:

```text
course created
course updated
course deleted
training updated
syllabus changed
note deleted
question set imported
```

The chatbot receives the event and refreshes or deletes the affected source data in ChromaDB.

## When To Use

Call this endpoint after successful database commit in the Java backend.

Recommended integration points:

| Java Event | Call Webhook? | Payload |
| :--- | :--- | :--- |
| Course created | Yes | `event_type: created`, `source_type: course`, `source_ids: [course:id]` |
| Course updated | Yes | `event_type: updated`, `source_type: course`, `source_ids: [course:id]` |
| Course deleted | Yes | `event_type: deleted`, `source_type: course`, `source_ids: [course:id]` |
| Training created/updated/deleted | Yes | `source_type: training` |
| Notes/syllabus/question data changed | Yes | matching `source_type` |
| User profile changed | No | Not RAG knowledge |
| Payment/order changed | No | Not RAG knowledge |
| Admin login changed | No | Not RAG knowledge |

## Request Body

```json
{
  "event_id": "evt-unique-id-001",
  "event_type": "updated",
  "source_type": "training",
  "source_ids": [
    "training:Spring Boot Training with Spring Security and Redis Caching"
  ],
  "occurred_at": "2026-05-25T02:16:26+05:45"
}
```

## Field Rules

| Field | Required | Type | Notes |
| :--- | :---: | :--- | :--- |
| `event_id` | Yes | string | Unique event ID from Java backend |
| `event_type` | Yes | string | `created`, `updated`, `deleted`, or `refresh` |
| `source_type` | Yes | string | One of the supported source types |
| `source_ids` | Yes | string array | One or more source IDs |
| `occurred_at` | Yes | ISO datetime | Event time |

## Curl

```bash
curl -X POST "${CHATBOT_BASE_URL}/webhooks/sync" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${CHATBOT_API_KEY}" \
  -d '{
    "event_id": "evt-training-updated-001",
    "event_type": "updated",
    "source_type": "training",
    "source_ids": [
      "training:Spring Boot Training with Spring Security and Redis Caching"
    ],
    "occurred_at": "2026-05-25T02:16:26+05:45"
  }'
```

## Expected Response

```json
{
  "accepted": true,
  "event_id": "evt-training-updated-001",
  "source_type": "training",
  "source_ids": [
    "training:Spring Boot Training with Spring Security and Redis Caching"
  ]
}
```

## Java DTO

```java
import java.time.OffsetDateTime;
import java.util.List;

public record ChatbotWebhookSyncRequest(
        String event_id,
        String event_type,
        String source_type,
        List<String> source_ids,
        OffsetDateTime occurred_at
) {}
```

## Java WebClient Example

```java
public Mono<String> notifyChatbotSync(
        String eventType,
        String sourceType,
        List<String> sourceIds
) {
    ChatbotWebhookSyncRequest request = new ChatbotWebhookSyncRequest(
            UUID.randomUUID().toString(),
            eventType,
            sourceType,
            sourceIds,
            OffsetDateTime.now()
    );

    return webClient.post()
            .uri("/webhooks/sync")
            .header("Content-Type", "application/json")
            .header("X-API-Key", apiKey)
            .bodyValue(request)
            .retrieve()
            .bodyToMono(String.class);
}
```

---

# 7. Recommended Spring Boot Event Integration Pattern

Call the webhook **after the Java database transaction commits**.

This avoids notifying the chatbot about data that was rolled back.

## Example With Transactional Event Listener

```java
public record CourseChangedEvent(
        String eventType,
        Long courseId
) {}
```

```java
@Service
public class CourseService {

    private final ApplicationEventPublisher eventPublisher;

    @Transactional
    public Course updateCourse(Long id, CourseUpdateRequest request) {
        Course course = repository.findById(id).orElseThrow();
        course.setName(request.name());
        Course saved = repository.save(course);

        eventPublisher.publishEvent(new CourseChangedEvent("updated", saved.getId()));
        return saved;
    }
}
```

```java
@Component
public class ChatbotSyncEventListener {

    private final ChatbotAdminClient chatbotAdminClient;

    public ChatbotSyncEventListener(ChatbotAdminClient chatbotAdminClient) {
        this.chatbotAdminClient = chatbotAdminClient;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onCourseChanged(CourseChangedEvent event) {
        String sourceId = "course:" + event.courseId();

        chatbotAdminClient.notifyChatbotSync(
                event.eventType(),
                "course",
                List.of(sourceId)
        ).subscribe(
                response -> log.info("Chatbot sync accepted: {}", response),
                error -> log.warn("Chatbot sync failed: {}", error.getMessage())
        );
    }
}
```

> [!IMPORTANT]
> Do not block the user's create/update/delete request waiting for chatbot sync to finish. Fire the webhook asynchronously after commit, log failure, and retry if needed.

---

# 8. Delete Events

For deleted records, the Java backend should still send the original source ID.

Example:

```json
{
  "event_id": "evt-course-deleted-8",
  "event_type": "deleted",
  "source_type": "course",
  "source_ids": ["course:8"],
  "occurred_at": "2026-05-25T02:16:26+05:45"
}
```

Recommended Java pattern:

```java
@Transactional
public void deleteCourse(Long id) {
    Course course = repository.findById(id).orElseThrow();
    repository.delete(course);
    eventPublisher.publishEvent(new CourseChangedEvent("deleted", id));
}
```

---

# 9. Retry and Failure Handling

The Java backend should treat chatbot sync as **eventual consistency**.

If the chatbot API is temporarily down:

```text
main Java DB transaction should still succeed
sync event should be retried later
admin can run /admin/sync or /admin/refresh manually if needed
```

Recommended retry approach:

1. Send webhook after commit.
2. If request fails, store event in an outbox table.
3. Background scheduler retries failed events.
4. Mark event completed after `2xx` response.

## Simple Outbox Table Example

```text
chatbot_sync_outbox
- id
- event_id
- event_type
- source_type
- source_ids_json
- occurred_at
- status: PENDING / SENT / FAILED
- attempts
- last_error
- created_at
- updated_at
```

## Retry Rules

| Failure | Recommended Action |
| :--- | :--- |
| `401 Unauthorized` | Do not retry endlessly; API key/config is wrong |
| `422 Validation Error` | Do not retry blindly; payload shape/source type is wrong |
| `500` | Retry with backoff |
| timeout/connect error | Retry with backoff |
| chatbot down | Retry later |

---

# 10. `GET /api/v1/metrics`

## Purpose

Monitoring endpoint for uptime/Prometheus-style checks.

## When To Use

Use this endpoint from:

- Prometheus
- uptime monitor
- Docker health check
- deployment smoke test

## Request

```http
GET /api/v1/metrics
```

No API key is required.

## Curl

```bash
curl "${CHATBOT_BASE_URL}/metrics"
```

## Expected Response

```text
entrance_chatbot_up 1
```

---

# 11. Health and Readiness APIs

Although not listed in your question, these are useful for Java/backend deployment and monitoring.

## Health

```bash
curl "${CHATBOT_BASE_URL}/health"
```

Expected:

```json
{"status":"ok"}
```

## Readiness

```bash
curl "${CHATBOT_BASE_URL}/readiness"
```

Expected:

```json
{
  "status": "ready",
  "components": {
    "redis": {"status": "ok", "detail": null},
    "chromadb": {"status": "ok", "detail": null},
    "ollama": {"status": "ok", "detail": null}
  }
}
```

Use readiness before routing traffic to the chatbot backend.

---

# 12. Source ID Convention

The chatbot expects stable source IDs.

Recommended format:

| Entity | Source Type | Source ID Format |
| :--- | :--- | :--- |
| Course | `course` | `course:{id}` |
| College | `college` | `college:{id}` |
| Syllabus | `syllabus` | `syllabus:{id}` |
| Note | `note` | `note:{id}` |
| Old Question | `old_question` | `old_question:{id}` |
| Training | `training` | `training:{id-or-slug}` |
| Question Set | `question_set` | `question_set:{id}` |
| Question | `question` | `question:{id}` |

> [!IMPORTANT]
> Keep source IDs deterministic. If a source ID changes, the chatbot may store duplicate or stale ChromaDB chunks.

---

# 13. Recommended Integration Timeline

## During Initial Deployment

1. Start chatbot backend.
2. Check health:

```bash
curl "${CHATBOT_BASE_URL}/health"
```

3. Check readiness:

```bash
curl "${CHATBOT_BASE_URL}/readiness"
```

4. Run full refresh:

```bash
curl -X POST "${CHATBOT_BASE_URL}/admin/refresh" \
  -H "X-API-Key: ${CHATBOT_API_KEY}"
```

5. Check stats:

```bash
curl -H "X-API-Key: ${CHATBOT_API_KEY}" \
  "${CHATBOT_BASE_URL}/admin/stats"
```

## During Normal Operation

1. Java backend creates/updates/deletes RAG knowledge data.
2. Java publishes internal domain event.
3. After transaction commit, Java calls:

```text
POST /api/v1/webhooks/sync
```

4. If webhook fails, store/retry with outbox.

## During Admin Maintenance

Use:

```text
POST /api/v1/admin/sync
```

for one source type or source ID.

Use:

```text
POST /api/v1/admin/refresh
```

for full rebuilds.

---

# 14. Minimal Java Client Checklist

Implement these in Java backend:

- [ ] `chatbot.base-url` config
- [ ] `chatbot.api-key` secret config
- [ ] `ChatbotAdminClient` using `WebClient`
- [ ] DTO for `/webhooks/sync`
- [ ] DTO for `/admin/sync`
- [ ] `@TransactionalEventListener(AFTER_COMMIT)` for RAG entities
- [ ] retry/outbox mechanism for failed sync events
- [ ] admin-only endpoint/button to call `/admin/refresh`
- [ ] admin-only endpoint/button to call `/admin/stats`
- [ ] deployment smoke check for `/health`, `/readiness`, `/metrics`

---

# 15. What Not To Do

Do not:

- call `/admin/refresh` after every record update
- expose `X-API-Key` to browser/frontend code
- block user-facing Java requests until chatbot sync completes
- send webhook before the Java DB transaction commits
- use random source IDs that change over time
- retry `401`/`422` forever without fixing configuration or payload
- use admin APIs for normal student chatbot messages

Normal student chat should use:

```text
POST /api/v1/chat
POST /api/v1/chat/stream
```
