# Codex Project Instructions

## Project

This repository implements a generalized, multi-tenant enterprise multi-agent web platform.

The system supports five predefined intelligent departments:

- Customer Support
- Human Resources
- Information Technology
- Finance
- Procurement

Before planning, coding, or changing architecture, read the relevant files under `docs/`.

## Authoritative Documents

Start with:

1. `docs/01-system-overview.md`
2. `docs/02-actors-and-departments.md`
3. `docs/03-business-rules-and-request-lifecycle.md`
4. `docs/04-ai-multi-agent-architecture.md`
5. `docs/06-backend-architecture.md`
6. `docs/07-langgraph-workflow-architecture.md`
7. `docs/08-database-architecture.md`
8. `docs/18-codex-implementation-instructions.md`

These documents are the source of truth. Do not silently replace an accepted decision with a different architecture.

## Fundamental Rules

- Every business request has exactly one owner department.
- Collaborating departments work on the same Request ID.
- The system does not create sub-requests.
- The Router selects the owner department and also acts as the Platform Assistant.
- The Router may ask at most three clarification questions.
- Department agents may dynamically plan and revise future steps.
- Workflow state is stored outside the LLM.
- Department agents do not have persistent local memory.
- Inter-department communication uses structured objects.
- Temporary inter-department messages are not permanently stored.
- Human approval and action must be minimized.
- Before involving a human, agents must complete all possible research, validation, comparison, calculation, and summarization.
- Important decisions may receive one independent reviewer-feedback cycle.
- Unsupported operations create a capability-gap notification and terminate gracefully.
- All tenant-owned database access must be scoped to the authenticated company.
- The frontend communicates only with the FastAPI backend.
- Live request updates use Server-Sent Events.
- Version 1 uses one centralized LangGraph graph.
- Version 1 uses a feature-based modular monolith.
- Version 1 supports only the five predefined departments.

## Technology Direction

- Frontend: React + TypeScript
- Backend: Python + FastAPI
- Orchestration: LangGraph
- Supporting AI components: LangChain where useful
- ORM: SQLAlchemy 2.0
- Migrations: Alembic
- Relational database: hosted PostgreSQL on Neon
- Vector database: hosted Pinecone
- Real-time updates: Server-Sent Events

## Working Method

For complex work:

1. Read the relevant specification.
2. Summarize the requirement and affected modules.
3. Identify conflicts or missing decisions before coding.
4. Propose a small implementation plan.
5. Implement incrementally.
6. Add tests for important behavior.
7. Run tests, linting, and type checks.
8. Report what changed and any remaining limitations.

Do not implement unrelated functionality. Do not add extra databases, microservices, agents, selectors, or infrastructure unless a documented requirement needs them.

## Definition of Done

A task is complete only when:

- it follows the architecture documents;
- tenant isolation is preserved;
- important failure cases are handled;
- relevant tests pass;
- migrations are included when schema changes are made;
- API schemas are typed;
- no secrets are committed;
- documentation is updated when behavior changes.
