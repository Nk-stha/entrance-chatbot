# Frontend Integration Guide

This guide explains which chatbot APIs should be integrated into the existing frontend, how to call them, and which APIs must stay server/admin-only.

> [!IMPORTANT]
> Do not create a new frontend app in this chatbot backend project. Integrate these APIs into the existing Entrance Gateway frontend.

---

# 1. Frontend API Integration Summary

## Public Browser-Safe APIs

These APIs can be called from frontend browser code.

| API | Method | Use In Frontend? | Purpose |
| :--- | :--- | :---: | :--- |
| `/api/v1/chat` | `POST` | Yes | Normal non-streaming chatbot response |
| `/api/v1/chat/stream` | `POST` | Yes | Streaming chatbot response with SSE-style events |
| `/api/v1/health` | `GET` | Optional | Simple service health check |
| `/api/v1/readiness` | `GET` | Optional | Dependency readiness check: Redis, ChromaDB, Ollama |
| `/api/v1/metrics` | `GET` | No for UI, yes for monitoring | Prometheus/monitoring metric output |

## Server/Admin-Only APIs

Do **not** call these directly from public browser JavaScript.

| API | Method | Use In Public Frontend? | Why Not? |
| :--- | :--- | :---: | :--- |
| `/api/v1/admin/refresh` | `POST` | No | Requires `X-API-Key`; full ingestion rebuild |
| `/api/v1/admin/sync` | `POST` | No | Requires `X-API-Key`; targeted ingestion sync |
| `/api/v1/admin/stats` | `GET` | No public use | Requires `X-API-Key`; admin-only ChromaDB stats |
| `/api/v1/webhooks/sync` | `POST` | No | Java backend-to-chatbot sync endpoint |

> [!CAUTION]
> Never expose `API_KEY` in frontend/browser code. If an admin dashboard needs admin APIs, call them from a secure server-side route, not directly from the browser.

---

# 2. Environment Variable

For local development:

```env
NEXT_PUBLIC_CHATBOT_API_BASE_URL=http://localhost:8002/api/v1
```

For production:

```env
NEXT_PUBLIC_CHATBOT_API_BASE_URL=https://your-chatbot-backend-domain.com/api/v1
```

Example usage:

```ts
const CHATBOT_API_BASE_URL = process.env.NEXT_PUBLIC_CHATBOT_API_BASE_URL!;
```

---

# 3. Main User Chat API

## `POST /api/v1/chat`

Use this when:

- you want a simple request/response chatbot flow
- you do not need token-by-token streaming
- you want the easiest frontend integration
- you are testing the chatbot quickly

### Request Body

```ts
type ChatRequest = {
  message: string;
  session_id?: string | null;
  filters?: {
    source_type?: string;
    source_id?: string;
    category?: string;
  } | null;
  top_k?: number;
};
```

### Example Request

```json
{
  "message": "Which training teaches Redis caching?",
  "session_id": "web-chat-session-001",
  "filters": null,
  "top_k": 5
}
```

### Example Response

```json
{
  "answer": "The training that teaches Redis caching is Spring Boot Training with Spring Security and Redis Caching [1].",
  "confidence": 0.758,
  "sources": [
    {
      "number": "1",
      "chunk_id": "training:Spring Boot Training with Spring Security and Redis Caching:chunk:0",
      "document_id": "training:Spring Boot Training with Spring Security and Redis Caching",
      "source_id": "training:Spring Boot Training with Spring Security and Redis Caching",
      "source_type": "training",
      "title": "Spring Boot Training with Spring Security and Redis Caching"
    }
  ],
  "session_id": "web-chat-session-001",
  "allowed": true,
  "reason": "grounded"
}
```

### TypeScript Client

```ts
export type ChatSource = {
  number: string;
  chunk_id: string;
  document_id: string;
  source_id: string;
  source_type: string;
  title: string;
};

export type ChatResponse = {
  answer: string;
  confidence: number;
  sources: ChatSource[];
  session_id: string;
  allowed: boolean;
  reason: string;
};

export type ChatRequest = {
  message: string;
  session_id?: string | null;
  filters?: {
    source_type?: string;
    source_id?: string;
    category?: string;
  } | null;
  top_k?: number;
};

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_CHATBOT_API_BASE_URL!;

  const response = await fetch(`${baseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: getOrCreateChatSessionId(),
      filters: null,
      top_k: 5,
      ...request,
    }),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Chat request failed: ${response.status} ${message}`);
  }

  return response.json();
}

export function getOrCreateChatSessionId(): string {
  const key = "eg_chat_session_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;

  const created = crypto.randomUUID();
  localStorage.setItem(key, created);
  return created;
}
```

---

# 4. Streaming Chat API

## `POST /api/v1/chat/stream`

Use this when:

- you want ChatGPT-like token streaming
- you want faster perceived response time
- you want to show “assistant is typing” behavior
- you want citations/sources after generation completes

The backend streams Server-Sent-Event-style chunks over a `POST` response.

Because browser `EventSource` only supports `GET`, use `fetch()` and parse the response stream.

---

## Streaming Event Types

| Event | Meaning | Example Data |
| :--- | :--- | :--- |
| `heartbeat` | Backend is still working | `{"status":"working"}` |
| `token` | One generated text token | `{"token":"BCA"}` |
| `sources` | Final citation/source metadata | `{"sources":[...],"confidence":0.758,"allowed":true,"reason":"grounded"}` |
| `done` | Final answer and confidence | `{"answer":"...","confidence":0.758}` |
| `error` | Streaming error | `{"message":"..."}` |

Expected healthy order:

```text
heartbeat optional
→ token repeated
→ sources
→ done
```

---

## TypeScript Streaming Client

```ts
export type StreamHandlers = {
  onToken: (token: string) => void;
  onSources: (payload: {
    sources: ChatSource[];
    confidence: number;
    allowed: boolean;
    reason: string;
  }) => void;
  onDone: (payload: { answer: string; confidence: number }) => void;
  onError: (message: string) => void;
  onHeartbeat?: () => void;
};

export async function streamChatMessage(
  request: ChatRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal
) {
  const baseUrl = process.env.NEXT_PUBLIC_CHATBOT_API_BASE_URL!;

  const response = await fetch(`${baseUrl}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: JSON.stringify({
      session_id: getOrCreateChatSessionId(),
      filters: null,
      top_k: 5,
      ...request,
    }),
  });

  if (!response.ok || !response.body) {
    const message = await response.text();
    throw new Error(`Stream request failed: ${response.status} ${message}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      handleSseEvent(rawEvent, handlers);
    }
  }
}

function handleSseEvent(rawEvent: string, handlers: StreamHandlers) {
  const lines = rawEvent.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLine = lines.find((line) => line.startsWith("data: "));

  if (!eventLine || !dataLine) return;

  const event = eventLine.replace("event: ", "").trim();
  const data = JSON.parse(dataLine.replace("data: ", ""));

  if (event === "heartbeat") handlers.onHeartbeat?.();
  if (event === "token") handlers.onToken(data.token);
  if (event === "sources") handlers.onSources(data);
  if (event === "done") handlers.onDone(data);
  if (event === "error") handlers.onError(data.message ?? "Streaming failed");
}
```

---

# 5. React Usage Example

```tsx
import { useRef, useState } from "react";

export function ChatBox() {
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function submit() {
    if (!input.trim()) return;

    setAnswer("");
    setSources([]);
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChatMessage(
        {
          message: input,
          session_id: getOrCreateChatSessionId(),
          filters: null,
          top_k: 5,
        },
        {
          onHeartbeat: () => setLoading(true),
          onToken: (token) => setAnswer((current) => current + token),
          onSources: (payload) => setSources(payload.sources),
          onDone: (payload) => {
            setAnswer(payload.answer);
            setLoading(false);
          },
          onError: (message) => {
            setAnswer(message);
            setLoading(false);
          },
        },
        controller.signal
      );
    } catch (error) {
      setAnswer(error instanceof Error ? error.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <section>
      <textarea
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="Ask about courses, trainings, syllabus, or entrance preparation..."
      />

      <button onClick={submit} disabled={loading || !input.trim()}>
        {loading ? "Thinking..." : "Ask"}
      </button>

      <button onClick={() => abortRef.current?.abort()} disabled={!loading}>
        Stop
      </button>

      <article>{answer}</article>

      <SourceList sources={sources} />
    </section>
  );
}
```

---

# 6. Citation Rendering

Answers contain inline citations:

```text
BCA is Bachelor in Computer Application [1].
```

The response includes matching source metadata:

```json
[
  {
    "number": "1",
    "chunk_id": "course:8:chunk:0",
    "document_id": "course:8",
    "source_id": "course:8",
    "source_type": "course",
    "title": "BCA"
  }
]
```

Frontend can render:

```tsx
function SourceList({ sources }: { sources: ChatSource[] }) {
  if (!sources.length) return null;

  return (
    <aside>
      <h3>Sources</h3>
      {sources.map((source) => (
        <button key={`${source.number}-${source.chunk_id}`} title={source.source_type}>
          [{source.number}] {source.title}
        </button>
      ))}
    </aside>
  );
}
```

---

# 7. Filters

Frontend can optionally pass filters.

## No Filter: General Chat

Recommended default:

```json
{
  "message": "Which computer-related courses and trainings are available?",
  "session_id": "web-chat-session-001",
  "filters": null,
  "top_k": 5
}
```

## Course Filter

Use only if the UI is inside a course-specific page/tab.

```json
{
  "message": "Which courses are semester-based?",
  "session_id": "web-chat-session-001",
  "filters": {
    "source_type": "course"
  },
  "top_k": 5
}
```

## Training Filter

Use only if the UI is inside a training-specific page/tab.

```json
{
  "message": "Which training teaches Redis caching?",
  "session_id": "web-chat-session-001",
  "filters": {
    "source_type": "training"
  },
  "top_k": 5
}
```

> [!TIP]
> For the main chatbot widget, prefer `filters: null`. Let retrieval search across all data unless the user is clearly inside a scoped page.

---

# 8. Session Memory

Use a stable `session_id` so the chatbot can remember recent turns.

Recommended browser storage:

```ts
const key = "eg_chat_session_id";
localStorage.setItem(key, crypto.randomUUID());
```

When to create a new session:

- user clicks “New chat”
- user logs out
- user switches account
- old session should be cleared for privacy

Example “New Chat” button:

```ts
export function resetChatSession() {
  localStorage.removeItem("eg_chat_session_id");
}
```

---

# 9. Error Handling

Handle these cases in frontend UI:

| Status/Event | Meaning | UI Behavior |
| :--- | :--- | :--- |
| `200` + `allowed: true` | Normal grounded answer | Show answer and sources |
| `200` + `allowed: false` | Refusal/guardrail response | Show refusal text, no fake sources |
| `401` | Should not happen for public chat | Check wrong endpoint/API key misuse |
| `422` | Invalid request body | Show validation error and log payload |
| `429` | Rate limited | Show “Too many requests, try again soon” |
| `500` | Backend error | Show retry message |
| stream `error` | Streaming failure | Stop typing state and show error |
| network error | Chatbot unavailable | Show fallback error message |

Example:

```ts
if (response.status === 429) {
  throw new Error("Too many chatbot requests. Please try again shortly.");
}
```

---

# 10. Optional Health/Readiness UI

For an internal admin UI, you may call:

```text
GET /api/v1/health
GET /api/v1/readiness
```

Do not show raw dependency details to public users. For public UI, a simple fallback is enough:

```text
Chatbot is currently unavailable. Please try again later.
```

---

# 11. Admin APIs in Frontend Admin Dashboard

If an admin dashboard needs buttons like:

```text
Refresh chatbot data
Sync one source
View ChromaDB stats
```

then the browser should call your **Java/Next.js server-side API route**, and that server-side route should call the chatbot admin API with `X-API-Key`.

Do not call chatbot admin APIs directly from the browser.

Recommended flow:

```text
Browser admin UI
→ your existing backend / server route
→ chatbot admin API with X-API-Key
```

Example server-side route behavior:

```text
POST /admin/chatbot/refresh
→ server reads CHATBOT_API_KEY from environment
→ server calls POST /api/v1/admin/refresh
→ server returns sanitized response to browser
```

---

# 12. CORS

Backend CORS is controlled by:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Add your existing frontend domain here.

Examples:

```env
CORS_ORIGINS=http://localhost:3000,https://entrancegateway.com,https://www.entrancegateway.com
```

After changing `.env`, restart backend:

```bash
docker compose up -d --build backend
```

---

# 13. Quick Local Tests

## Normal Chat

```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is BCA?",
    "session_id": "demo-session-1",
    "filters": null,
    "top_k": 5
  }'
```

## Streaming Chat

```bash
curl -N -X POST http://localhost:8002/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which training teaches Redis caching?",
    "session_id": "demo-session-stream-1",
    "filters": null,
    "top_k": 5
  }'
```

## Expected Streaming Events

```text
event: heartbeat
data: {"status":"working"}

event: token
data: {"token":"..."}

event: sources
data: {"sources":[...],"confidence":0.758,"allowed":true,"reason":"grounded"}

event: done
data: {"answer":"...","confidence":0.758}
```

---

# 14. Frontend Integration Checklist

- [ ] Add `NEXT_PUBLIC_CHATBOT_API_BASE_URL`
- [ ] Implement `sendChatMessage()` for `/chat`
- [ ] Implement `streamChatMessage()` for `/chat/stream`
- [ ] Store stable `session_id` in localStorage
- [ ] Add “New chat” reset behavior
- [ ] Render answer text
- [ ] Render inline citations and source list
- [ ] Handle `allowed: false` refusal responses
- [ ] Handle `429` rate limit responses
- [ ] Handle stream `heartbeat`, `token`, `sources`, `done`, and `error`
- [ ] Add stop/cancel button using `AbortController`
- [ ] Configure backend `CORS_ORIGINS`
- [ ] Keep admin API key out of browser code

---

# 15. What Not To Integrate Directly in Public Frontend

Do not directly call these from browser code:

```text
POST /api/v1/admin/refresh
POST /api/v1/admin/sync
GET  /api/v1/admin/stats
POST /api/v1/webhooks/sync
```

Reason:

```text
They require privileged credentials or are intended for Java backend/internal operations.
```

Public frontend should mainly integrate:

```text
POST /api/v1/chat
POST /api/v1/chat/stream
```
