# Logical Data Flow Diagram - Entrance Chatbot

> Image verification note: `image/logical-dfd.png` has been checked against the current repository implementation. A report-ready verification and explanation is available in `docs/logicaldfd.md`. The image is logically consistent with the implemented learner question-answering, searchable knowledge maintenance, conversation context, synchronization control, admin status, and monitoring workflows, with minor academic clarifications about webhook origin, implicit answer-grounding validation, and monitoring scope.

## Source Basis and Evidence Limits

This Logical DFD is based only on repository evidence:

- `docs/planning/RAG_CHATBOT_PHASE_0_CONTRACT.md`: backend-only scope, knowledge sources, chat, memory, webhook, and reconciliation contracts.
- `docs/api.md`: public chat, streaming chat, admin, webhook, metrics, session, source, and error payloads.
- `docs/frontend-integration.md`: existing frontend integration and browser-safe versus admin-only operations.
- `docs/java-backend-chatbot-api-integration.md`: business use of full refresh, targeted sync, stats, webhook events, and monitoring.
- `docs/planning/RAG_KNOWLEDGE_SOURCE_APIS.md`: authoritative business knowledge categories.
- `phase/phase_13.md` and `phase/phase_15.md`: verified public, admin, webhook, monitoring, memory, and hardening behavior.

No UI screen source files are present in this repository. The documented UI boundary is an existing Entrance Gateway frontend. The DFD therefore names the external actor as "Learner / Website User" rather than inventing screen names.

One source conflict exists: the Phase 0 text mentions webhook event type `bulk_refresh`, while the current API/model documentation uses `refresh`. This DFD uses `refresh` because it is present in the current webhook model and Java integration guide.

## Missing Business Information

No clarification is required to model the documented chatbot subsystem. The following details are not present in the repository and are therefore not modeled:

- Named business roles beyond learner/user, administrator/operations user, source-content backend, and monitoring service.
- A real admin UI workflow, except the documented possibility of an admin dashboard/tool.
- Human moderation, analytics review, billing, authentication for public chat users, or user profile workflows.
- PDF/file content extraction, because v1 explicitly excludes it.
- Blog and quiz-attempt ingestion, because v1 excludes them from global knowledge.

## Yourdon & DeMarco Notation Used

- External Entity: `[E# Entity Name]`
- Process: `(P# Verb Object)`
- Data Store: `||D# Data Store Name||`
- Data Flow: noun phrase on an arrow

Processes are named with verb phrases. Data flows and stores are named with noun phrases.

## 1. Context Diagram - Level 0

```text
[E1 Learner / Website User]
    -- chat question, session identifier, optional knowledge filter -->
        (0 Provide Entrance Gateway Chatbot Service)
    <-- grounded answer, citations, confidence, refusal or stream events --

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

### Context Reasoning

The system exists to answer learner questions from Entrance Gateway knowledge, keep chatbot knowledge synchronized with the authoritative content system, support administrator refresh/sync/status operations, and expose operational status for monitoring. These are the business-facing responsibilities documented in the API, frontend integration, Java integration, and Phase 0/13 documents.

## 2. Level 1 Logical DFD

```text
[E1 Learner / Website User]
    -- chat question -->
        (1.0 Answer Learner Question)
    <-- chatbot answer --

[E1 Learner / Website User]
    -- session identifier -->
        (1.0 Answer Learner Question)
    <-- citation list, confidence result, refusal reason --

(1.0 Answer Learner Question)
    -- conversation turn -->
        ||D2 Conversation Context||
(1.0 Answer Learner Question)
    <-- recent conversation context --
        ||D2 Conversation Context||
(1.0 Answer Learner Question)
    -- knowledge query -->
        ||D1 Searchable Knowledge||
(1.0 Answer Learner Question)
    <-- relevant knowledge excerpts --
        ||D1 Searchable Knowledge||

[E2 Entrance Gateway Content System]
    -- source knowledge records -->
        (2.0 Maintain Searchable Knowledge)
    <-- source record request --

[E2 Entrance Gateway Content System]
    -- content change event -->
        (2.0 Maintain Searchable Knowledge)
    <-- sync acknowledgement --

[E3 Administrator / Operations User]
    -- refresh or sync request -->
        (2.0 Maintain Searchable Knowledge)
    <-- ingestion or sync report --

(2.0 Maintain Searchable Knowledge)
    -- normalized knowledge excerpts -->
        ||D1 Searchable Knowledge||
(2.0 Maintain Searchable Knowledge)
    -- source change record -->
        ||D3 Synchronization Control||
(2.0 Maintain Searchable Knowledge)
    <-- processed event record, source payload fingerprint --
        ||D3 Synchronization Control||

[E3 Administrator / Operations User]
    -- knowledge status request -->
        (3.0 Report Operational Status)
    <-- knowledge status --

[E4 Monitoring Service]
    -- service status request -->
        (3.0 Report Operational Status)
    <-- service status metric --

(3.0 Report Operational Status)
    -- knowledge status query -->
        ||D1 Searchable Knowledge||
(3.0 Report Operational Status)
    <-- knowledge status summary --
        ||D1 Searchable Knowledge||
```

### Level 1 Process Reasoning

- `1.0 Answer Learner Question` is required because public chat and streaming chat are the learner-facing business workflow.
- `2.0 Maintain Searchable Knowledge` is required because the chatbot only answers from synchronized Entrance Gateway knowledge and supports full refresh, targeted sync, webhooks, and reconciliation.
- `3.0 Report Operational Status` is required because the system exposes knowledge status and service status for administration and monitoring.

## 3. Level 2 Logical DFDs

### 3.1 Level 2 for Process 1.0 - Answer Learner Question

```text
[E1 Learner / Website User]
    -- chat question, session identifier, optional knowledge filter -->
        (1.1 Receive Learner Question)
    -- validated question -->
        (1.2 Assemble Question Context)

(1.2 Assemble Question Context)
    -- session lookup -->
        ||D2 Conversation Context||
(1.2 Assemble Question Context)
    <-- recent conversation context --
        ||D2 Conversation Context||
(1.2 Assemble Question Context)
    -- search request -->
        (1.3 Find Relevant Knowledge)

(1.3 Find Relevant Knowledge)
    -- knowledge query, optional knowledge filter -->
        ||D1 Searchable Knowledge||
(1.3 Find Relevant Knowledge)
    <-- relevant knowledge excerpts --
        ||D1 Searchable Knowledge||
(1.3 Find Relevant Knowledge)
    -- source-backed answer context -->
        (1.4 Compose Grounded Answer)

(1.4 Compose Grounded Answer)
    -- draft answer and source references -->
        (1.5 Validate Answer Grounding)

(1.5 Validate Answer Grounding)
    -- conversation turn -->
        ||D2 Conversation Context||
(1.5 Validate Answer Grounding)
    -- chatbot answer, citation list, confidence result, refusal reason -->
        [E1 Learner / Website User]
```

#### Process 1.0 Reasoning

The documented chat workflow receives a question, uses the session identifier for recent context, retrieves relevant knowledge, builds a source-grounded answer, validates citations/grounding, returns an answer or refusal, and stores the conversation turn.

### 3.2 Level 2 for Process 2.0 - Maintain Searchable Knowledge

```text
[E3 Administrator / Operations User]
    -- full refresh request, targeted sync request -->
        (2.1 Receive Knowledge Maintenance Request)

[E2 Entrance Gateway Content System]
    -- content change event -->
        (2.1 Receive Knowledge Maintenance Request)

(2.1 Receive Knowledge Maintenance Request)
    -- accepted maintenance instruction -->
        (2.2 Determine Knowledge Scope)

(2.2 Determine Knowledge Scope)
    -- processed event lookup, payload fingerprint lookup -->
        ||D3 Synchronization Control||
(2.2 Determine Knowledge Scope)
    <-- processed event record, source payload fingerprint --
        ||D3 Synchronization Control||
(2.2 Determine Knowledge Scope)
    -- source record request -->
        [E2 Entrance Gateway Content System]
[E2 Entrance Gateway Content System]
    -- source knowledge records -->
        (2.3 Prepare Knowledge Documents)

(2.3 Prepare Knowledge Documents)
    -- normalized knowledge documents -->
        (2.4 Divide Knowledge Documents)
(2.4 Divide Knowledge Documents)
    -- searchable knowledge excerpts -->
        (2.5 Store Searchable Knowledge)
(2.5 Store Searchable Knowledge)
    -- normalized knowledge excerpts -->
        ||D1 Searchable Knowledge||
(2.5 Store Searchable Knowledge)
    -- source change record -->
        ||D3 Synchronization Control||

(2.1 Receive Knowledge Maintenance Request)
    -- sync acknowledgement -->
        [E2 Entrance Gateway Content System]
(2.5 Store Searchable Knowledge)
    -- ingestion or sync report -->
        [E3 Administrator / Operations User]
```

#### Process 2.0 Reasoning

The documented maintenance workflows include administrator full refresh, administrator targeted sync, automatic content-change events, fetch of authoritative source records, normalization into human-readable documents, chunking/excerpt creation, storage of searchable knowledge, and idempotency/change tracking.

### 3.3 Level 2 for Process 3.0 - Report Operational Status

```text
[E3 Administrator / Operations User]
    -- knowledge status request -->
        (3.1 Receive Status Request)
[E4 Monitoring Service]
    -- service status request -->
        (3.1 Receive Status Request)

(3.1 Receive Status Request)
    -- knowledge status query -->
        (3.2 Check Knowledge Availability)
(3.2 Check Knowledge Availability)
    -- knowledge status query -->
        ||D1 Searchable Knowledge||
(3.2 Check Knowledge Availability)
    <-- knowledge status summary --
        ||D1 Searchable Knowledge||

(3.1 Receive Status Request)
    -- service status query -->
        (3.3 Check Service Availability)

(3.2 Check Knowledge Availability)
    -- knowledge status -->
        [E3 Administrator / Operations User]
(3.3 Check Service Availability)
    -- service status metric -->
        [E4 Monitoring Service]
```

#### Process 3.0 Reasoning

The documented status workflows separate administrator knowledge status from monitoring service availability status. Knowledge status depends on stored searchable knowledge; service status is an operational status response.

## 4. External Entities

| ID | External Entity | Description | Evidence |
|---|---|---|---|
| E1 | Learner / Website User | Person using the existing Entrance Gateway frontend to ask chatbot questions. | Frontend docs and public chat API. |
| E2 | Entrance Gateway Content System | Authoritative business system that owns course, college, syllabus, note, old question, question set, question, and training data; sends content-change events. | Phase 0 contract, knowledge source inventory, Java integration guide. |
| E3 | Administrator / Operations User | Authorized user or admin tool that triggers full refresh, targeted sync, and knowledge status checks. | Admin API and Java integration guide. |
| E4 | Monitoring Service | External status checker that requests service metrics. | Metrics API and Java integration guide. |

## 5. Processes

| ID | Process | Purpose |
|---|---|---|
| 0 | Provide Entrance Gateway Chatbot Service | Whole chatbot subsystem boundary. |
| 1.0 | Answer Learner Question | Return a grounded chatbot answer, citation list, confidence, or refusal. |
| 1.1 | Receive Learner Question | Accept and validate a learner's question, session identifier, and optional knowledge filter. |
| 1.2 | Assemble Question Context | Combine the current question with recent conversation context. |
| 1.3 | Find Relevant Knowledge | Select source excerpts relevant to the learner's question. |
| 1.4 | Compose Grounded Answer | Produce an answer from the selected source-backed context. |
| 1.5 | Validate Answer Grounding | Ensure the answer is supported by sources; return refusal when context is insufficient. |
| 2.0 | Maintain Searchable Knowledge | Keep chatbot knowledge aligned with authoritative Entrance Gateway content. |
| 2.1 | Receive Knowledge Maintenance Request | Accept admin maintenance requests and content-change events. |
| 2.2 | Determine Knowledge Scope | Decide which source type or source records require refresh, deletion, or no-op handling. |
| 2.3 | Prepare Knowledge Documents | Convert source records into normalized, human-readable knowledge documents. |
| 2.4 | Divide Knowledge Documents | Split normalized documents into searchable excerpts while preserving source identity. |
| 2.5 | Store Searchable Knowledge | Add, replace, or delete searchable excerpts and record synchronization state. |
| 3.0 | Report Operational Status | Provide knowledge and service status to authorized or monitoring actors. |
| 3.1 | Receive Status Request | Accept status requests from administrators or monitoring services. |
| 3.2 | Check Knowledge Availability | Report searchable knowledge availability and counts. |
| 3.3 | Check Service Availability | Report basic chatbot service availability. |

## 6. Data Stores

| ID | Data Store | Description |
|---|---|---|
| D1 | Searchable Knowledge | Source-backed knowledge excerpts with source identity, title, category, citation metadata, and searchable representation. |
| D2 | Conversation Context | Recent conversation turns associated with a session identifier. |
| D3 | Synchronization Control | Processed event identifiers and source payload fingerprints used to avoid duplicate or unchanged reprocessing. |

## 7. Data Flows

| From | To | Data Flow |
|---|---|---|
| E1 | 0 / 1.1 | chat question |
| E1 | 0 / 1.1 | session identifier |
| E1 | 0 / 1.1 | optional knowledge filter |
| 0 / 1.5 | E1 | chatbot answer |
| 0 / 1.5 | E1 | citation list |
| 0 / 1.5 | E1 | confidence result |
| 0 / 1.5 | E1 | refusal reason |
| 1.1 | 1.2 | validated question |
| 1.2 | D2 | session lookup |
| D2 | 1.2 | recent conversation context |
| 1.2 | 1.3 | search request |
| 1.3 | D1 | knowledge query |
| 1.3 | D1 | optional knowledge filter |
| D1 | 1.3 | relevant knowledge excerpts |
| 1.3 | 1.4 | source-backed answer context |
| 1.4 | 1.5 | draft answer and source references |
| 1.5 | D2 | conversation turn |
| E2 | 0 / 2.1 | authoritative knowledge records |
| E2 | 0 / 2.1 | content change event |
| 0 / 2.2 | E2 | source record request |
| 0 / 2.1 | E2 | sync acknowledgement |
| E3 | 0 / 2.1 | full refresh request |
| E3 | 0 / 2.1 | targeted sync request |
| 2.1 | 2.2 | accepted maintenance instruction |
| 2.2 | D3 | processed event lookup |
| 2.2 | D3 | payload fingerprint lookup |
| D3 | 2.2 | processed event record |
| D3 | 2.2 | source payload fingerprint |
| 2.3 | 2.4 | normalized knowledge documents |
| 2.4 | 2.5 | searchable knowledge excerpts |
| 2.5 | D1 | normalized knowledge excerpts |
| 2.5 | D3 | source change record |
| 2.5 | E3 | ingestion or sync report |
| E3 | 0 / 3.1 | knowledge status request |
| E4 | 0 / 3.1 | service status request |
| 3.1 | 3.2 | knowledge status query |
| 3.2 | D1 | knowledge status query |
| D1 | 3.2 | knowledge status summary |
| 3.2 | E3 | knowledge status |
| 3.1 | 3.3 | service status query |
| 3.3 | E4 | service status metric |

## 8. Data Dictionary

### Data Flows

| Data Flow | Description | Structure |
|---|---|---|
| chat question | Learner's natural-language question. | message text |
| session identifier | Conversation identifier owned by the frontend/user session. | session id |
| optional knowledge filter | Optional constraint on source type, source id, or category. | source type, source id, category |
| validated question | Accepted learner question after input validation. | message text, session id, optional filter |
| search request | Business request to find knowledge relevant to the question. | question text, recent context, optional filter |
| knowledge query | Searchable form of the learner's question. | query text, filter, requested result count |
| relevant knowledge excerpts | Source-backed excerpts selected for answer generation. | excerpt text, source id, source type, title, citation number, relevance score |
| source-backed answer context | Relevant excerpts organized for answer composition. | numbered excerpts, citation map |
| draft answer and source references | Candidate answer with referenced sources. | answer text, citation markers, source references |
| chatbot answer | Final answer returned to learner. | answer text |
| citation list | Sources supporting the answer. | number, source id, source type, title, chunk/excerpt id |
| confidence result | System confidence/grounding result. | numeric confidence, allowed flag |
| refusal reason | Explanation category when answer cannot be safely provided. | reason code or fallback message |
| recent conversation context | Recent prior turns for the same session. | ordered user/assistant messages |
| conversation turn | Current user question and final assistant answer. | session id, user message, assistant response |
| authoritative knowledge records | Current source content owned by Entrance Gateway. | course, college, syllabus, note, old question, question set, question, training records |
| content change event | Notification that source content changed. | event id, event type, source type, source ids, occurred time |
| source record request | Request for current source records or specific source ids. | source type, source ids or all records |
| sync acknowledgement | Acceptance response for a content-change event. | accepted flag, event id, source type, source ids |
| full refresh request | Admin request to refresh all supported knowledge. | authorization, refresh command |
| targeted sync request | Admin request to refresh one source type or one source id. | source type, optional source id |
| accepted maintenance instruction | Validated instruction to perform refresh, sync, update, delete, or no-op. | maintenance type, source type, source ids |
| processed event lookup | Lookup for duplicate event detection. | event id |
| payload fingerprint lookup | Lookup for unchanged content detection. | source id |
| processed event record | Stored record that an event was already handled. | event id, processed flag |
| source payload fingerprint | Stored fingerprint of previous source content. | source id, content fingerprint |
| normalized knowledge documents | Human-readable source documents prepared from source records. | id, title, content, metadata, raw source reference |
| searchable knowledge excerpts | Smaller source-backed knowledge units. | excerpt id, document id, content, metadata |
| normalized knowledge excerpts | Excerpts stored for future question answering. | excerpt id, content, source identity, metadata |
| source change record | Synchronization control update after processing source content. | event id, source id, payload fingerprint |
| ingestion or sync report | Outcome of a refresh or sync operation. | success flag, counts, errors |
| knowledge status request | Admin request for stored knowledge status. | authorization, status command |
| knowledge status query | Request to inspect searchable knowledge availability. | collection/status query |
| knowledge status summary | Summary of available searchable knowledge. | knowledge collection name, count |
| knowledge status | Admin-facing knowledge availability result. | collection name, count |
| service status request | Monitoring request for chatbot availability. | status command |
| service status query | Internal request to check service availability. | status command |
| service status metric | Monitoring-facing service availability metric. | up/down status metric |

### Data Stores

| Data Store | Data Elements |
|---|---|
| Searchable Knowledge | excerpt id, document id, source type, source id, source primary id, title, category, tags, url or file reference, updated time, version, content/excerpt text, citation metadata, searchable representation |
| Conversation Context | session id, recent user message, recent assistant answer, message role, created time, expiry rule |
| Synchronization Control | event id, processed marker, source id, source type, payload/content fingerprint, processing time |

## 9. Process Specifications - PSPEC

### PSPEC 1.1 - Receive Learner Question

Validate that the learner provided a non-empty question and a usable session identifier. Accept optional knowledge filters when provided. Output a validated question for context assembly or return a validation error outside the normal successful DFD flow.

### PSPEC 1.2 - Assemble Question Context

Use the session identifier to request recent conversation context. Combine current question, optional filter, and recent context into a search request. Do not create an answer in this process.

### PSPEC 1.3 - Find Relevant Knowledge

Use the search request to retrieve relevant source-backed knowledge excerpts from Searchable Knowledge. Apply any provided source type, source id, or category filter. Output relevant knowledge excerpts or an empty source-backed context if no adequate source exists.

### PSPEC 1.4 - Compose Grounded Answer

Create a draft answer using only source-backed answer context. Include source references for factual claims. If the source-backed context is empty, prepare a refusal candidate rather than inventing unsupported content.

### PSPEC 1.5 - Validate Answer Grounding

Check whether the draft answer is supported by valid source references. Return a final answer with citations and confidence when grounded. Return the documented fallback/refusal when support is insufficient. Store the final conversation turn for later session continuity.

### PSPEC 2.1 - Receive Knowledge Maintenance Request

Accept full refresh requests, targeted sync requests, and content-change events. Confirm that protected maintenance actions are authorized according to the business contract. Output accepted maintenance instructions and immediate sync acknowledgement where applicable.

### PSPEC 2.2 - Determine Knowledge Scope

Determine whether the maintenance instruction affects all knowledge, one source type, one source record, or deleted source records. Check processed event records and payload fingerprints to avoid duplicate or unchanged work. Request current source records when refresh or update is required.

### PSPEC 2.3 - Prepare Knowledge Documents

Convert authoritative source records into normalized human-readable knowledge documents. Preserve source identity, title, category, tags, and source references. Do not include unsupported business sources such as blogs or quiz attempts in global chatbot knowledge.

### PSPEC 2.4 - Divide Knowledge Documents

Divide normalized documents into smaller searchable knowledge excerpts. Preserve document identity, source identity, title, and ordering metadata on each excerpt.

### PSPEC 2.5 - Store Searchable Knowledge

Add or replace searchable excerpts for created/updated/refreshed content. Remove searchable excerpts for deleted content. Update synchronization records and return an ingestion or sync report.

### PSPEC 3.1 - Receive Status Request

Accept administrator knowledge status requests and monitoring service status requests. Route each request to the appropriate status-checking process.

### PSPEC 3.2 - Check Knowledge Availability

Inspect Searchable Knowledge and return a knowledge status summary to the administrator, including the documented collection identity/count style information.

### PSPEC 3.3 - Check Service Availability

Return basic service availability information to the monitoring service.

## 10. Balancing Verification

### Context Diagram to Level 1

| Context Flow | Preserved in Level 1? | Evidence |
|---|---:|---|
| chat question | Yes | E1 to 1.0 |
| session identifier | Yes | E1 to 1.0 |
| optional knowledge filter | Yes | E1 to 1.0 |
| grounded answer/chatbot answer | Yes | 1.0 to E1 |
| citations | Yes | 1.0 to E1 |
| confidence/refusal | Yes | 1.0 to E1 |
| authoritative knowledge records | Yes | E2 to 2.0 |
| content change event | Yes | E2 to 2.0 |
| source record request | Yes | 2.0 to E2 |
| sync acknowledgement | Yes | 2.0 to E2 |
| full refresh request | Yes | E3 to 2.0 |
| targeted sync request | Yes | E3 to 2.0 |
| ingestion/sync report | Yes | 2.0 to E3 |
| knowledge status request | Yes | E3 to 3.0 |
| knowledge status | Yes | 3.0 to E3 |
| service status request | Yes | E4 to 3.0 |
| service status metric | Yes | 3.0 to E4 |

### Level 1 Process 1.0 to Level 2

Balanced. Inputs to 1.0 from E1 are preserved through 1.1. Outputs from 1.0 to E1 are produced by 1.5. Level 1 interaction with D1 is represented by 1.3. Level 1 interaction with D2 is represented by 1.2 and 1.5.

### Level 1 Process 2.0 to Level 2

Balanced. Inputs to 2.0 from E2 and E3 are preserved through 2.1. Outputs to E2 and E3 are preserved through 2.1 and 2.5. D1 updates are preserved through 2.5. D3 lookup and update flows are preserved through 2.2 and 2.5.

### Level 1 Process 3.0 to Level 2

Balanced. Inputs to 3.0 from E3 and E4 are preserved through 3.1. Outputs to E3 and E4 are preserved through 3.2 and 3.3. D1 status access is preserved through 3.2.

## 11. DFD Rule Verification

| Rule | Result |
|---|---|
| No external entity directly exchanges data with another external entity. | Passed |
| No data store directly exchanges data with another data store. | Passed |
| No external entity directly reads from or writes to a data store. | Passed |
| Every data store has at least one input and one output where business use requires both. | Passed |
| Every process has at least one input and at least one output. | Passed |
| Process names use verb phrases. | Passed |
| Data flow names use noun phrases. | Passed |
| Child diagrams preserve parent inputs and outputs. | Passed |

## 12. Black Hole, Miracle, and Gray Hole Check

| Process | Black Hole? | Miracle? | Gray Hole? | Reason |
|---|---:|---:|---:|---|
| 1.0 Answer Learner Question | No | No | No | Receives question/session/filter and stored context/knowledge; returns answer/citations/refusal and stores turn. |
| 2.0 Maintain Searchable Knowledge | No | No | No | Receives admin/event/source records and sync state; stores knowledge/control data and returns reports/acknowledgements. |
| 3.0 Report Operational Status | No | No | No | Receives status requests and stored status inputs; returns status outputs. |
| 1.1 Receive Learner Question | No | No | No | Validates incoming question data and passes it forward. |
| 1.2 Assemble Question Context | No | No | No | Uses validated question and context store; emits search request. |
| 1.3 Find Relevant Knowledge | No | No | No | Uses search request and knowledge store; emits relevant excerpts. |
| 1.4 Compose Grounded Answer | No | No | No | Uses source-backed context; emits draft answer and references. |
| 1.5 Validate Answer Grounding | No | No | No | Uses draft answer and references; emits answer/refusal and stores turn. |
| 2.1 Receive Knowledge Maintenance Request | No | No | No | Uses admin/event input; emits accepted instruction and acknowledgement. |
| 2.2 Determine Knowledge Scope | No | No | No | Uses instruction and sync controls; emits source requests or scope decisions. |
| 2.3 Prepare Knowledge Documents | No | No | No | Uses source records; emits normalized documents. |
| 2.4 Divide Knowledge Documents | No | No | No | Uses normalized documents; emits excerpts. |
| 2.5 Store Searchable Knowledge | No | No | No | Uses excerpts or delete scope; updates stores and emits report. |
| 3.1 Receive Status Request | No | No | No | Uses status request; emits routed status query. |
| 3.2 Check Knowledge Availability | No | No | No | Uses status query and searchable knowledge; emits knowledge status. |
| 3.3 Check Service Availability | No | No | No | Uses service status query; emits service status metric. |
