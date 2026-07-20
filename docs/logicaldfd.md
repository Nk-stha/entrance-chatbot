# Logical Data Flow Diagram Verification - Entrance Chatbot

## 1. Purpose

This document verifies the Logical Data Flow Diagram (Logical DFD) shown in `image/logical-dfd.png` against the implemented Entrance Chatbot system. It is written in academic report style and explains the business-level processes, data stores, data flows, balancing, and diagram accuracy.

## 2. Verification Verdict

The Logical DFD in `image/logical-dfd.png` matches the implemented system at the business-process level. It correctly represents the chatbot as a system that:

- Receives learner questions.
- Uses recent conversation context.
- Retrieves relevant knowledge.
- Generates grounded answers with citations or refusal.
- Maintains searchable knowledge from the Entrance Gateway content system.
- Tracks synchronization state.
- Reports knowledge and service status to administrators and monitoring services.

The diagram is suitable for an academic report with a few clarifications:

| Diagram Item | Verification Result | Explanation |
|---|---|---|
| `E1 Learner / Website User` | Matches | The chatbot is designed for browser/frontend users who submit questions and receive grounded answers. |
| `E2 Entrance Gateway Content System` | Matches | The external content system is represented by the Java backend API that owns source records. |
| `E3 Administrator / Operations User` | Matches | Admin users can request refresh, targeted sync, and knowledge status. |
| `E4 Monitoring Service` | Matches | Monitoring tools can request health/readiness/metrics. |
| `1.0 Answer Learner Question` | Matches | Implemented by the chat and streaming chat workflow. |
| `2.0 Maintain Searchable Knowledge` | Matches | Implemented by admin refresh, admin sync, webhook sync, ingestion, normalization, chunking, embedding, and vector storage. |
| `3.0 Report Operational Status` | Matches | Implemented by health, readiness, metrics, and admin stats endpoints. |
| `D1 Searchable Knowledge` | Matches | Implemented physically by ChromaDB. Logically, it stores searchable knowledge excerpts. |
| `D2 Conversation Context` | Matches | Implemented physically by Redis session memory. |
| `D3 Synchronization Control` | Matches | Implemented physically by Redis webhook event markers and payload hashes. |
| `(Webhook) Content Change Event` | Mostly matches | Logically valid as an event source. Physically, this event enters through the Java backend webhook endpoint `/api/v1/webhooks/sync`. |
| `1.5 Format & Respond` | Mostly matches | The implementation also performs citation and grounding validation before responding. This validation is implicit in the diagram's final response process. |
| Monitoring and knowledge status | Partially simplified | Admin stats inspect stored knowledge. Monitoring mainly checks service health/readiness/metrics rather than business knowledge status. |

Overall, the diagram is logically correct and balanced. It abstracts away physical technologies such as FastAPI, Redis, ChromaDB, and Ollama, which is appropriate for a Logical DFD.

## 3. Evidence Used

The verification is based on repository evidence from:

- `backend/api/chat.py`: learner chat and streaming chat endpoints.
- `backend/memory/session.py`: conversation context storage and retrieval.
- `backend/retrieval/retriever.py`: knowledge retrieval from indexed content.
- `backend/generation/prompt_builder.py`: prompt and grounded answer preparation.
- `backend/generation/generator.py`: streaming response generation.
- `backend/generation/citation.py` and `backend/generation/hallucination.py`: citation and grounding validation.
- `backend/api/admin.py`: refresh, sync, and stats operations.
- `backend/api/webhooks.py`: content-change webhook sync.
- `backend/ingestion/pipeline.py`: knowledge maintenance orchestration.
- `backend/ingestion/api_client.py`: source record fetch from Java backend API.
- `backend/ingestion/normalizer.py` and `backend/ingestion/chunker.py`: preparation of searchable documents and chunks.
- `backend/retrieval/vector_store.py`: searchable knowledge storage.
- `backend/api/health.py` and `backend/api/router.py`: operational status and metrics.
- `backend/models/domain.py` and `backend/models/webhook.py`: source types and webhook event structures.

## 4. Logical System Boundary

The logical system boundary is the Entrance Chatbot service. The Logical DFD does not focus on software frameworks, containers, ports, or databases. Instead, it focuses on what the system does from a business and information-flow perspective.

Inside the system boundary:

- Answering learner questions.
- Maintaining searchable knowledge.
- Managing conversation context.
- Maintaining synchronization control information.
- Reporting operational and knowledge status.

Outside the system boundary:

- Learners or website users.
- The Entrance Gateway content system.
- Administrators or operations users.
- Monitoring services.

## 5. Context Diagram Explanation

At Level 0, the whole chatbot subsystem is represented as one process: `(0) Provide Entrance Gateway Chatbot Service`.

```text
[E1 Learner / Website User]
    -- chat question, session identifier, optional knowledge filter -->
        (0 Provide Entrance Gateway Chatbot Service)
    <-- grounded answer, citations, confidence, refusal, or stream events --

[E2 Entrance Gateway Content System]
    -- authoritative knowledge records, content change event -->
        (0 Provide Entrance Gateway Chatbot Service)
    <-- knowledge sync request, source record request, sync acknowledgement --

[E3 Administrator / Operations User]
    -- full refresh request, targeted sync request, knowledge status request -->
        (0 Provide Entrance Gateway Chatbot Service)
    <-- ingestion report, sync report, knowledge status --

[E4 Monitoring Service]
    -- service status request -->
        (0 Provide Entrance Gateway Chatbot Service)
    <-- service status metric --
```

This context diagram matches the system because the chatbot's main responsibilities are answering questions, synchronizing knowledge, and reporting status. No external actor directly accesses the internal logical data stores.

## 6. Level 1 Logical DFD Explanation

The Level 1 DFD decomposes the chatbot into three major logical processes.

### 6.1 Process 1.0 - Answer Learner Question

This process handles the learner-facing use case. A learner provides a question and session identifier. The system uses conversation context and searchable knowledge to produce a grounded answer.

Inputs:

- Chat question.
- Session identifier.
- Optional knowledge filter.
- Recent conversation context.
- Relevant knowledge excerpts.

Outputs:

- Answer.
- Citations.
- Confidence result.
- Refusal reason when the answer cannot be safely grounded.
- Updated conversation turn.

This process matches the implementation because `POST /api/v1/chat` and `POST /api/v1/chat/stream` both read session history, retrieve knowledge when needed, generate an answer, validate grounding, and store the conversation turn.

### 6.2 Process 2.0 - Maintain Searchable Knowledge

This process keeps chatbot knowledge aligned with the authoritative Entrance Gateway content system.

Inputs:

- Source knowledge records.
- Content change events.
- Admin refresh requests.
- Admin targeted sync requests.
- Existing synchronization records and payload fingerprints.

Outputs:

- Normalized searchable knowledge excerpts.
- Updated synchronization control records.
- Source record requests.
- Sync acknowledgements.
- Ingestion or sync reports.

This process matches the implementation because the ingestion pipeline fetches source records, normalizes them, chunks them, embeds them, stores them for retrieval, and updates synchronization state.

### 6.3 Process 3.0 - Report Operational Status

This process supports administration and monitoring.

Inputs:

- Knowledge status request from an administrator.
- Service status request from a monitoring service.
- Searchable knowledge status information.

Outputs:

- Knowledge status.
- Service status metric.

This process matches the implementation through admin stats, health, readiness, and metrics endpoints.

## 7. Level 2 Logical DFD Explanation

### 7.1 Level 2 for Process 1.0 - Answer Learner Question

The image decomposes learner question answering into five logical sub-processes:

```text
[E1 Learner / Website User]
    -- question, session id -->
        (1.1 Receive Question)
    -- validated question -->
        (1.2 Retrieve Context)
    -- search query -->
        (1.3 Retrieve Knowledge)
    -- context and excerpts -->
        (1.4 Generate Answer)
    -- raw/final answer -->
        (1.5 Format and Respond)
    <-- answer, citations, confidence, refusal, or stream events --
```

Detailed mapping:

| Logical Process | Implementation Mapping | Explanation |
|---|---|---|
| `1.1 Receive Question` | `ChatRequest` in `backend/api/chat.py` | Validates message, session id, optional filters, and result count. |
| `1.2 Retrieve Context` | `SessionMemory.format_recent_history()` | Reads recent conversation context for the session. |
| `1.3 Retrieve Knowledge` | `Retriever.retrieve()` | Finds relevant ChromaDB chunks using dense retrieval, keyword retrieval, reranking, and filters. |
| `1.4 Generate Answer` | Prompt builder and Ollama generation client | Builds a grounded prompt and generates answer text from source-backed context. |
| `1.5 Format and Respond` | Citation/hallucination guardrails and response serialization | Validates citations, computes confidence, formats sources, saves the conversation turn, and returns JSON or stream events. |

Academic clarification: The implementation contains explicit grounding and citation validation. The image's `1.5 Format & Respond` process should be understood to include this validation step before the response is returned.

### 7.2 Level 2 for Process 2.0 - Maintain Searchable Knowledge

The image decomposes knowledge maintenance into source ingestion, normalization, indexing, and sync control.

```text
[E2 Entrance Gateway Content System]
    -- source records -->
        (2.1 Ingest Source Data)
    -- raw source data -->
        (2.2 Normalize and Chunk)
    -- normalized chunks -->
        (2.3 Index Knowledge)
    -- indexed chunks -->
        ||D1 Searchable Knowledge||

[Webhook Content Change Event]
    -- change event -->
        (2.3 Index Knowledge)
    -- update record -->
        (2.4 Update Sync Control)
    -- sync control record -->
        ||D3 Synchronization Control||
```

Detailed mapping:

| Logical Process | Implementation Mapping | Explanation |
|---|---|---|
| `2.1 Ingest Source Data` | `BackendAPIClient` | Fetches source records from the Java backend API. |
| `2.2 Normalize and Chunk` | `normalize_sources()` and `chunk_documents()` | Converts source records into normalized documents and searchable chunks. |
| `2.3 Index Knowledge` | `OllamaEmbedder` and `VectorStore.upsert_chunks()` | Creates embeddings and stores indexed chunks in searchable knowledge. |
| `2.4 Update Sync Control` | Redis logic in `IngestionPipeline` | Stores processed event markers and payload hashes. |

Supported logical source records:

- Course records.
- College records.
- Syllabus records.
- Note records.
- Old question records.
- Training records.
- Question set records.
- Question records.

Academic clarification: In the physical implementation, the webhook event is received through the Java backend webhook API and is authenticated using `X-API-Key`. The Logical DFD shows it as a separate event source to emphasize the business event, which is acceptable in a logical model.

### 7.3 Level 2 for Process 3.0 - Report Operational Status

The image decomposes operational reporting into knowledge status, service health, and response aggregation.

```text
[E3 Administrator / Operations User]
    -- knowledge status request -->
        (3.1 Get Knowledge Status)
    -- knowledge status summary -->
        (3.3 Aggregate and Respond)

[E4 Monitoring Service]
    -- service status request -->
        (3.2 Get Service Health)
    -- service status metric -->
        (3.3 Aggregate and Respond)
```

Detailed mapping:

| Logical Process | Implementation Mapping | Explanation |
|---|---|---|
| `3.1 Get Knowledge Status` | `/api/v1/admin/stats` | Returns collection name and count for searchable knowledge. |
| `3.2 Get Service Health` | `/health`, `/api/v1/health`, `/api/v1/health/ready` | Reports liveness and readiness. |
| `3.3 Aggregate and Respond` | API response serialization | Returns knowledge status to admin or service status metric to monitoring. |

Academic clarification: Monitoring does not directly query the logical `Synchronization Control` store in the current implementation. Monitoring checks service readiness, while admin stats check searchable knowledge. If the diagram visually suggests that monitoring reads sync control, that should be interpreted as a simplified status/reporting abstraction.

## 8. Logical Data Stores

| ID | Logical Store | Purpose | Physical Implementation |
|---|---|---|---|
| D1 | Searchable Knowledge | Stores normalized and indexed excerpts used to answer learner questions. | ChromaDB collection containing chunks, embeddings, documents, and metadata. |
| D2 | Conversation Context | Stores recent conversation turns for continuity within a session. | Redis key `rag:session:{session_id}` with TTL. |
| D3 | Synchronization Control | Stores processed event records and source payload fingerprints to avoid duplicate or unnecessary ingestion. | Redis keys `rag:webhook:event:{event_id}` and `rag:payload_hash:{source_id}`. |

## 9. Logical External Entities

| ID | External Entity | Role |
|---|---|---|
| E1 | Learner / Website User | Asks questions and receives chatbot answers. |
| E2 | Entrance Gateway Content System | Owns the authoritative knowledge records and provides source content for ingestion. |
| E3 | Administrator / Operations User | Triggers refresh/sync operations and checks knowledge status. |
| E4 | Monitoring Service | Checks service availability and receives status metrics. |

## 10. Logical Data Flows

| From | To | Data Flow | Description |
|---|---|---|---|
| E1 | 1.0 / 1.1 | Chat question | Natural-language learner question. |
| E1 | 1.0 / 1.1 | Session identifier | Identifier used to retrieve recent conversation context. |
| E1 | 1.0 / 1.1 | Optional knowledge filter | Optional source/category restriction for retrieval. |
| 1.5 | E1 | Grounded answer | Final chatbot answer based on available knowledge. |
| 1.5 | E1 | Citations | Source references used to support the answer. |
| 1.5 | E1 | Confidence | Grounding/confidence result. |
| 1.5 | E1 | Refusal or stream events | Refusal when insufficient evidence exists, or streaming output for stream endpoint. |
| 1.2 | D2 | Context lookup | Request for recent session turns. |
| D2 | 1.2 | Recent conversation context | Stored previous user and assistant messages. |
| 1.5 | D2 | Conversation turn | Current question and final assistant response. |
| 1.3 | D1 | Knowledge query | Request for relevant knowledge excerpts. |
| D1 | 1.3 | Relevant knowledge excerpts | Source-backed content used to answer. |
| E2 | 2.0 / 2.1 | Source knowledge records | Authoritative Entrance Gateway data records. |
| 2.0 / 2.1 | E2 | Source record request | Request for source content during ingestion. |
| E2 | 2.0 / 2.3 | Content change event | Business event indicating created, updated, deleted, or refreshed source content. |
| 2.0 | E2 | Sync acknowledgement | Response confirming webhook/sync acceptance. |
| E3 | 2.0 / 2.2 | Refresh or sync request | Admin command to refresh all data, a source type, or one source record. |
| 2.4 | E3 | Ingestion or sync report | Success flag, counts, and errors from maintenance operation. |
| 2.3 | D1 | Indexed knowledge chunks | Searchable excerpts stored for future retrieval. |
| 2.4 | D3 | Sync control record | Event marker or payload fingerprint update. |
| D3 | 2.0 | Processed event or payload fingerprint | Information used to skip duplicate events or unchanged records. |
| E3 | 3.1 | Knowledge status request | Admin request for searchable knowledge status. |
| 3.3 | E3 | Knowledge status | Collection/count style knowledge availability result. |
| E4 | 3.2 | Service status request | Monitoring request for liveness, readiness, or metrics. |
| 3.3 | E4 | Service status metric | Monitoring-facing health/readiness/metric output. |

## 11. Data Dictionary

| Data Item | Meaning |
|---|---|
| Chat question | The learner's submitted natural-language message. |
| Session identifier | A frontend-provided id used to group recent conversation messages. |
| Optional knowledge filter | Optional retrieval constraint such as source type, source id, or category. |
| Recent conversation context | Recent prior user and assistant messages for the same session. |
| Knowledge query | A request to find source excerpts relevant to the learner question. |
| Relevant knowledge excerpts | Searchable, source-backed chunks selected for answer generation. |
| Grounded answer | Final answer that is supported by retrieved source excerpts. |
| Citations | Source metadata returned with the answer so the learner can trace the answer. |
| Confidence | Numeric or logical indicator of answer grounding quality. |
| Refusal reason | Explanation or reason code when the answer is not allowed or cannot be grounded. |
| Source knowledge records | Authoritative content records from the Entrance Gateway content system. |
| Content change event | Event containing event id, event type, source type, source ids, and occurrence time. |
| Refresh or sync request | Administrator instruction to rebuild or update chatbot knowledge. |
| Indexed knowledge chunks | Normalized excerpts prepared for future retrieval. |
| Sync control record | Stored event marker or source payload fingerprint. |
| Ingestion report | Result of a knowledge maintenance run, including counts and errors. |
| Knowledge status | Summary of searchable knowledge availability. |
| Service status metric | Health, readiness, or Prometheus-style service status output. |

## 12. Process Specifications

### PSPEC 1.1 - Receive Question

Accept the learner's question, session identifier, and optional filter. Validate that the question and session identifier are present and within accepted limits. Pass the validated question forward for context retrieval.

### PSPEC 1.2 - Retrieve Context

Use the session identifier to retrieve recent conversation turns. Combine current question and recent history into a context summary for knowledge retrieval and answer generation.

### PSPEC 1.3 - Retrieve Knowledge

Search the logical Searchable Knowledge store for excerpts relevant to the learner question. Apply optional filters where provided. Return relevant excerpts and citation metadata.

### PSPEC 1.4 - Generate Answer

Use the selected excerpts and conversation context to generate an answer. For factual questions, the answer must be based on retrieved knowledge rather than unsupported model knowledge.

### PSPEC 1.5 - Format and Respond

Validate answer grounding, format citations and confidence, save the completed conversation turn, and return the final answer, refusal, or stream events to the learner.

### PSPEC 2.1 - Ingest Source Data

Request and receive authoritative source records from the Entrance Gateway content system. Convert received API data into internal source-fetch results for preparation.

### PSPEC 2.2 - Normalize and Chunk

Transform raw source records into human-readable knowledge documents and divide them into smaller searchable excerpts while preserving source identity and metadata.

### PSPEC 2.3 - Index Knowledge

Convert normalized chunks into indexed searchable knowledge and store them in the Searchable Knowledge data store. Handle created, updated, refreshed, or deleted source content according to the maintenance request.

### PSPEC 2.4 - Update Sync Control

Record processed events and source payload fingerprints. Return ingestion or sync reports to the administrator and acknowledgements to the content system.

### PSPEC 3.1 - Get Knowledge Status

Retrieve summary information about Searchable Knowledge, such as collection identity and stored record count, and pass it to the response process.

### PSPEC 3.2 - Get Service Health

Check logical service availability and dependency readiness. Pass health or readiness results to the response process.

### PSPEC 3.3 - Aggregate and Respond

Return the appropriate status response to the requester: knowledge status for administrators or service status metrics for monitoring systems.

## 13. Balancing Verification

### Context Diagram to Level 1

| Context Flow | Level 1 Preservation |
|---|---|
| Chat question, session identifier, optional knowledge filter | Preserved as E1 input to `1.0 Answer Learner Question`. |
| Grounded answer, citations, confidence, refusal, stream events | Preserved as output from `1.0` to E1. |
| Authoritative knowledge records | Preserved as E2 input to `2.0 Maintain Searchable Knowledge`. |
| Content change event | Preserved as E2/event input to `2.0`. |
| Knowledge sync request and source record request | Preserved as `2.0` output to E2. |
| Sync acknowledgement | Preserved as `2.0` output to E2. |
| Admin refresh, sync, and status requests | Preserved as E3 input to `2.0` and `3.0`. |
| Ingestion report, sync report, and knowledge status | Preserved as outputs to E3. |
| Service status request | Preserved as E4 input to `3.0`. |
| Service status metric | Preserved as output from `3.0` to E4. |

### Level 1 Process 1.0 to Level 2

Balanced. Learner input enters `1.1 Receive Question`. Conversation context access is represented by `1.2 Retrieve Context` and D2. Searchable knowledge access is represented by `1.3 Retrieve Knowledge` and D1. Final answer outputs are produced by `1.5 Format and Respond`.

### Level 1 Process 2.0 to Level 2

Balanced. Source records enter `2.1 Ingest Source Data`. Admin sync requests enter the knowledge maintenance flow. Content change events affect indexing and sync control. Searchable knowledge updates are written to D1, synchronization records are written to D3, and reports/acknowledgements leave the process.

### Level 1 Process 3.0 to Level 2

Balanced. Administrator knowledge status requests are handled by `3.1 Get Knowledge Status`. Monitoring service status requests are handled by `3.2 Get Service Health`. `3.3 Aggregate and Respond` returns the correct status output to the correct external entity.

## 14. DFD Rule Verification

| DFD Rule | Result |
|---|---|
| External entities do not directly exchange data with one another through the DFD. | Passed. |
| External entities do not directly read or write internal data stores. | Passed. |
| Data stores do not directly exchange data with other data stores. | Passed. |
| Each process has at least one input and one output. | Passed. |
| Data flows are named using data-oriented nouns or noun phrases. | Passed. |
| Processes are named as actions. | Passed. |
| Level 2 diagrams preserve the parent process inputs and outputs. | Passed. |

## 15. Black Hole, Miracle, and Gray Hole Check

| Process | Black Hole? | Miracle? | Gray Hole? | Reason |
|---|---:|---:|---:|---|
| `1.0 Answer Learner Question` | No | No | No | It receives question/context/knowledge and returns an answer or refusal. |
| `2.0 Maintain Searchable Knowledge` | No | No | No | It receives source/admin/event inputs and produces searchable knowledge, sync records, reports, and acknowledgements. |
| `3.0 Report Operational Status` | No | No | No | It receives status requests and returns status outputs. |
| `1.1 Receive Question` | No | No | No | It validates learner input and passes a validated question forward. |
| `1.2 Retrieve Context` | No | No | No | It uses the session id to produce recent context. |
| `1.3 Retrieve Knowledge` | No | No | No | It uses a search query and Searchable Knowledge to produce relevant excerpts. |
| `1.4 Generate Answer` | No | No | No | It uses context and excerpts to generate an answer. |
| `1.5 Format and Respond` | No | No | No | It formats, validates, stores the turn, and returns the response. |
| `2.1 Ingest Source Data` | No | No | No | It receives or requests source records and produces raw source data for preparation. |
| `2.2 Normalize and Chunk` | No | No | No | It transforms source data into normalized chunks. |
| `2.3 Index Knowledge` | No | No | No | It writes indexed chunks to searchable knowledge and sends update data to sync control. |
| `2.4 Update Sync Control` | No | No | No | It records synchronization state and emits reports. |
| `3.1 Get Knowledge Status` | No | No | No | It receives admin status requests and produces status summaries. |
| `3.2 Get Service Health` | No | No | No | It receives monitoring requests and produces service health information. |
| `3.3 Aggregate and Respond` | No | No | No | It receives status summaries and returns them to the correct external actors. |

## 16. Academic Report Notes

The Logical DFD describes what the Entrance Chatbot does without depending on specific implementation technologies. It shows the chatbot as a knowledge-based question-answering subsystem connected to four external entities: learner, content system, administrator, and monitoring service.

The first major process, `Answer Learner Question`, represents the business function of helping learners get answers from Entrance Gateway knowledge. The learner sends a question with a session identifier. The system retrieves recent conversation context, finds relevant searchable knowledge, generates a grounded answer, validates the response, stores the turn, and returns the answer with citations or a refusal. This supports reliable answering because the chatbot is expected to answer from controlled knowledge rather than unsupported assumptions.

The second major process, `Maintain Searchable Knowledge`, represents the knowledge management function. The chatbot depends on the Entrance Gateway content system for authoritative records. When administrators request refresh/sync or content changes occur, the system ingests records, normalizes them, chunks them, indexes them, and updates synchronization control. This keeps the searchable knowledge base aligned with the source system and prevents unnecessary repeated processing.

The third major process, `Report Operational Status`, represents administrative and monitoring visibility. Administrators can request knowledge status, while monitoring tools can request service health or metrics. This supports operational reliability because the system exposes whether knowledge and required services are available.

The three logical data stores are also appropriate. `Searchable Knowledge` stores the content used for answering, `Conversation Context` stores recent session-based history, and `Synchronization Control` stores information needed to manage content freshness and duplicate events. These stores are logical abstractions; their physical implementations are ChromaDB and Redis, which are described in the Physical DFD.

## 17. Final Conclusion

The Logical DFD in `image/logical-dfd.png` is consistent with the Entrance Chatbot system. It correctly models the main logical processes, external entities, data stores, and data flows. The diagram is balanced and follows standard DFD rules. For academic use, the report should mention that webhook events physically arrive through the Java backend API, answer grounding validation is included inside the final response workflow, and monitoring primarily checks service health rather than directly inspecting synchronization control. With these clarifications, the Logical DFD is accurate and suitable for inclusion in the academic report.
