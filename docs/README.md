# Entrance Chatbot Documentation

This folder contains the organized markdown documentation for the RAG chatbot backend.

## Structure

```text
docs/
├── planning/   # Architecture, contracts, API inventory, roadmap
├── setup/      # Operational runbooks and setup notes
├── api.md      # Public/admin/webhook API contract
├── frontend-integration.md
├── chatbot_qa_question_pack.md
└── final-deployment-checklist.md

phase/          # Phase-by-phase implementation explanations
```

## Planning Documents

| Document | Purpose |
|---|---|
| [Production RAG Chatbot Plan](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/planning/PRODUCTION_RAG_CHATBOT_PLAN.md) | Main architecture and implementation plan |
| [Implementation Phases](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/planning/RAG_CHATBOT_IMPLEMENTATION_PHASES.md) | Detailed phase roadmap |
| [Phase 0 Contract](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/planning/RAG_CHATBOT_PHASE_0_CONTRACT.md) | Locked requirements and API contracts |
| [Knowledge Source APIs](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/planning/RAG_KNOWLEDGE_SOURCE_APIS.md) | Spring Boot API inventory for ingestion |

## API and Integration Documents

| Document | Purpose |
|---|---|
| [API Contract](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/api.md) | Public chat, streaming, admin, webhook, metrics contract |
| [Java Backend Integration Guide](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/java-backend-chatbot-api-integration.md) | How and when the Java/Spring Boot backend should call admin, webhook, stats, and monitoring APIs |
| [Frontend Integration Guide](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/frontend-integration.md) | Existing frontend integration examples and SSE handling |
| [Chatbot QA Question Pack](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/chatbot_qa_question_pack.md) | Relevant, irrelevant, complex, and tricky test questions with curl examples |
| [VPS CI/CD Deployment Plan](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/vps-cicd-deployment-plan.md) | Production-ready CI/CD plan for deploying the Docker Compose chatbot stack to a VPS |
| [Production CI/CD Setup Checklist](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/production-cicd-setup-checklist.md) | Exact GitHub secrets, VPS files, first deploy steps, Nginx setup, and post-deploy checks |
| [Final Deployment Checklist](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/final-deployment-checklist.md) | Staging/production readiness checklist |
| [Postman Collection](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/postman_collection.json) | Optional Postman collection for API testing |

## Setup Documents

| Document | Purpose |
|---|---|
| [Phase 1 Infrastructure Setup](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/docs/setup/PHASE_1_INFRASTRUCTURE_SETUP.md) | How to run the Phase 1 infrastructure stack |

## Phase Notes

| Document | Purpose |
|---|---|
| [Phase Index](file:///home/rohan-shrestha/Desktop/entrance-gateway/entrance-chatbot/phase/README.md) | Links to all implementation phase files |
