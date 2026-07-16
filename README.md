# Enterprise Multi-Agent Platform

A generalized, multi-tenant web platform that provides AI-powered enterprise departments capable of answering questions, executing approved workflows, collaborating with other departments, and coordinating minimum necessary human actions.

## Supported Departments

- Customer Support
- Human Resources
- Information Technology
- Finance
- Procurement

## Planned Stack

- React + TypeScript
- Python + FastAPI
- LangGraph
- LangChain where useful
- SQLAlchemy 2.0 + Alembic
- Neon PostgreSQL
- Pinecone
- Server-Sent Events

## Documentation

The full system specification is under [`docs/`](docs/).

Recommended reading order:

1. `01-system-overview.md`
2. `02-actors-and-departments.md`
3. `03-business-rules-and-request-lifecycle.md`
4. `04-ai-multi-agent-architecture.md`
5. `05-technology-stack.md`
6. `06-backend-architecture.md`
7. `07-langgraph-workflow-architecture.md`
8. `08-database-architecture.md`
9. `09-rag-company-knowledge.md`
10. `10-api-architecture.md`
11. `11-realtime-request-tracking.md`
12. `12-frontend-architecture.md`
13. `13-company-onboarding-data-import.md`
14. `14-auth-permissions-multitenancy.md`
15. `15-failure-handling-notifications.md`
16. `16-deployment-architecture.md`
17. `17-future-improvements.md`
18. `18-codex-implementation-instructions.md`

The accepted architecture decisions are summarized in `docs/decisions/architecture-decisions.md`.
