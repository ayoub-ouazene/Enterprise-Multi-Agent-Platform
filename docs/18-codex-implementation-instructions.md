# 18. Codex Implementation Instructions

## 18.1 Purpose

These instructions explain how to use Codex in VS Code without depending on the original ChatGPT conversation.

## 18.2 Initial Repository Setup

Place this documentation package in the project repository.

Codex should always read `AGENTS.md`.

## 18.3 First Codex Prompt

Use:

```text
Read AGENTS.md and all documents it marks as authoritative.

Do not write code yet.

Summarize:
1. the product goal;
2. the supported actors and departments;
3. the request lifecycle;
4. the AI architecture;
5. the backend architecture;
6. the database approach;
7. unresolved implementation details;
8. any contradictions you detect.
```

Do not continue until the summary matches the specification.

## 18.4 Implementation Order

Recommended order:

1. repository skeleton;
2. FastAPI app and configuration;
3. SQLAlchemy and Alembic setup;
4. authentication and company context;
5. core company, user, department, employee models;
6. business request and workflow-event models;
7. repository and transaction patterns;
8. SSE request tracking;
9. centralized LangGraph state and skeleton;
10. Router / Platform Assistant;
11. RAG ingestion and retrieval;
12. Customer Support;
13. IT;
14. Finance;
15. Procurement;
16. HR;
17. reviewer;
18. human approval and action;
19. onboarding data import;
20. natural-language data editing;
21. frontend dashboards and tracking;
22. tests and deployment.

The department order may be adjusted, but the core platform should exist first.

## 18.5 Prompt Template for a Codex Task

```text
Goal:
Implement <specific feature>.

Required context:
Read AGENTS.md and:
- docs/<relevant-file>.md
- docs/<another-relevant-file>.md

Scope:
- <included item>
- <included item>

Out of scope:
- <excluded item>
- <excluded item>

Constraints:
- preserve one owner department per request;
- preserve tenant scoping;
- use service-controlled transactions;
- do not add new infrastructure;
- follow the documented module structure.

Done when:
- implementation is complete;
- migrations are included;
- tests pass;
- type checks pass;
- documentation is updated if behavior changed.
```

## 18.6 First Implementation Task

A good first coding task:

```text
Read AGENTS.md, docs/05-technology-stack.md, docs/06-backend-architecture.md,
docs/08-database-architecture.md, and docs/14-auth-permissions-multitenancy.md.

Create only the initial FastAPI project structure with:
- app factory or main app;
- settings management;
- async SQLAlchemy engine and session;
- Alembic configuration;
- health endpoint;
- placeholder feature modules;
- test configuration.

Do not implement agents, LangGraph, Pinecone, or business tables yet.
```

## 18.7 Reviewing Codex Changes

After Codex implements a task, ask:

```text
Review your implementation against the referenced architecture documents.

List:
1. which requirements are satisfied;
2. which requirements are not yet implemented;
3. any architecture deviations;
4. tests run and their results;
5. security or tenant-isolation risks.
```

## 18.8 Change Management

When the architecture changes:

1. update the relevant document;
2. update `architecture-decisions.md`;
3. then ask Codex to modify the code;
4. do not change code and documentation independently.
