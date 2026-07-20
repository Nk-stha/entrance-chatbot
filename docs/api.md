# Entrance Gateway Chatbot API Contract

## Base URL

Local Docker backend:

```text
http://localhost:8002/api/v1
```

Production should use your deployed backend domain with the same `/api/v1` prefix.

---

## Public Chat Endpoint

```http
POST /chat
```

Use this for non-streaming JSON chat responses.

### Request

```json
{
  "message": "What is BCA?",
  "session_id": "user-session-123",
  "filters": {
    "source_type": "course"
  },
  "top_k": 3
}
```

### Request Fields

| Field | Type | Required | Notes |
|---|---:|---:|---|
| `message` | string | yes | User question, 1-4000 chars |
| `session_id` | string | yes | Stable per browser/user chat session |
| `filters` | object/null | no | Optional retrieval filters |
| `filters.source_type` | string | no | Example: `course`, `note`, `notice` |
| `filters.source_id` | string | no | Example: `course:8` |
| `filters.category` | string | no | Optional category metadata |
| `top_k` | number/null | no | 1-10 final context chunks |

### Response

```json
{
  "answer": "BCA is Bachelor in Computer Application [1].",
  "confidence": 0.591,
  "sources": [
    {
      "number": "1",
      "chunk_id": "course:8:chunk:0",
      "document_id": "course:8",
      "source_id": "course:8",
      "source_type": "course",
      "title": "BCA"
    }
  ],
  "session_id": "user-session-123",
  "allowed": true,
  "reason": "grounded",
  "intent": "knowledge"
}
```

### Response Fields

| Field | Type | Notes |
|---|---:|---|
| `answer` | string | Final guarded answer |
| `confidence` | number | `1.0` for conversational turns, citation-derived otherwise |
| `sources` | array | Always `[]` for conversational turns |
| `allowed` | boolean | `false` when guardrails replaced the answer with the refusal |
| `reason` | string | `grounded`, `conversational`, `missing_citations`, `invalid_citations`, `no_sources`, `mixed_refusal_answer` |
| `intent` | string | `knowledge`, `greeting`, or `small_talk` |

### Conversational Turns

Greetings and small talk (`hi`, `good morning`, `namaste`, `how are you`,
`thank you`) are classified before retrieval and answered directly.

- They **bypass retrieval entirely** — no embedding call, no ChromaDB query.
- They return `sources: []` and `intent: "greeting"` or `"small_talk"`.
- Citation guardrails do not apply, so a greeting is never answered with the
  refusal message.

Classification is deliberately conservative: any message that is not purely
conversational stays on the grounded RAG path. A greeting prefix does not
downgrade a real question — `"hi, which colleges offer BCA?"` is classified as
`knowledge` and must still be answered with citations.

---

## Streaming Chat Endpoint

```http
POST /chat/stream
```

Use this for real-time typing/streaming responses.

### Request

Same body as `/chat`:

```json
{
  "message": "What is BCA?",
  "session_id": "user-session-123",
  "filters": {
    "source_type": "course"
  },
  "top_k": 3
}
```

### Response Content-Type

```http
text/event-stream
```

---

## SSE Event Types

### `token`

Emitted incrementally as the model generates text.

```text
event: token
data: {"token":"BCA is "}
```

Frontend should append `data.token` to the visible assistant answer.

### `sources`

Emitted after generation and guardrail validation.

```text
event: sources
data: {"sources":[{"number":"1","chunk_id":"course:8:chunk:0","document_id":"course:8","source_id":"course:8","source_type":"course","title":"BCA"}],"confidence":0.591,"allowed":true,"reason":"grounded","intent":"knowledge"}
```

Frontend should render these as citations/source cards.

For a conversational turn the event carries an empty source list:

```text
event: sources
data: {"sources":[],"confidence":1.0,"allowed":true,"reason":"conversational","intent":"greeting"}
```

### `done`

Emitted when the answer is complete.

```text
event: done
data: {"answer":"BCA is Bachelor in Computer Application [1].","confidence":0.591}
```

Frontend can use this to stop loading state.

### `error`

Emitted on safe fallback/error.

```text
event: error
data: {"message":"I don't have enough verified context to answer that from the available Entrance Gateway knowledge sources."}
```

Frontend should show `data.message` as the assistant response.

### `heartbeat`

Emitted during slow generation to keep the connection alive.

```text
event: heartbeat
data: {"status":"working"}
```

Frontend can ignore this or use it to keep loading UI active.

---

## Citation Payload Shape

```ts
type CitationSource = {
  number: string;
  chunk_id: string;
  document_id: string;
  source_id: string;
  source_type: string;
  title: string;
};
```

Inline citations in answers use `[1]`, `[2]`, etc. Match them to `sources[].number`.

---

## Error Payload Shape

Standard API errors:

```json
{
  "success": false,
  "error": {
    "code": "http_error",
    "message": "Invalid admin API key",
    "request_id": "..."
  }
}
```

Streaming errors:

```json
{
  "message": "I don't have enough verified context to answer that from the available Entrance Gateway knowledge sources."
}
```

---

## Session ID Handling

The frontend must generate and persist a stable `session_id` per conversation.

Recommended browser behavior:

```text
1. Generate UUID when a new chat starts.
2. Store it in localStorage/session state.
3. Send it with every `/chat` or `/chat/stream` request.
4. Create a new UUID when user starts a new chat.
```

Example:

```ts
const sessionId = localStorage.getItem("eg_chat_session_id") ?? crypto.randomUUID();
localStorage.setItem("eg_chat_session_id", sessionId);
```

---

## Admin Endpoints

Admin endpoints require:

```http
X-API-Key: <API_KEY>
```

Do **not** expose this key in public frontend code.

### Full Refresh

```http
POST /admin/refresh
```

### Incremental Sync

```http
POST /admin/sync
```

```json
{
  "source_type": "course",
  "source_id": "course:8"
}
```

### Stats

```http
GET /admin/stats
```

Example response:

```json
{"collection":"entrance_knowledge","count":3}
```

---

## Webhook Endpoint

Used by Java backend when source content changes.

```http
POST /webhooks/sync
```

Requires:

```http
X-API-Key: <API_KEY>
```

Request:

```json
{
  "event_id": "evt-123",
  "event_type": "updated",
  "source_type": "course",
  "source_ids": ["course:8"],
  "occurred_at": "2026-05-25T00:15:00Z"
}
```

---

## Metrics

```http
GET /metrics
```

Response:

```text
entrance_chatbot_up 1
```
