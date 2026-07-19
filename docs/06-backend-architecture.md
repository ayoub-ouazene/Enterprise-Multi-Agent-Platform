# 6. Backend Architecture

## 6.1 Style

The backend is a feature-based modular monolith.

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   ├── auth/
│   ├── companies/
│   ├── users/
│   ├── requests/
│   ├── workflow/
│   ├── departments/
│   │   ├── customer_support/
│   │   ├── hr/
│   │   ├── it/
│   │   ├── finance/
│   │   └── procurement/
│   ├── rag/
│   ├── realtime/
│   ├── notifications/
│   ├── onboarding/
│   └── database/
├── alembic/
└── tests/
```

## 6.2 Core Modules

### `core/`

- configuration;
- environment settings;
- shared exceptions;
- logging;
- security helpers;
- common enums and types.

### `auth/`

- authentication;
- authorization dependencies;
- current-user context;
- token issuance and verification.

### `companies/`

- company registration;
- configuration;
- company-level data management.

### `requests/`

- business-request CRUD;
- request lifecycle;
- request status;
- request history;
- request visibility.

### `workflow/`

Owns all LangGraph-specific orchestration:

- graph definition;
- shared state;
- routing;
- nodes;
- persistence;
- human pauses;
- reviewer flow;
- failure flow;
- completion.

### `departments/`

Each department owns:

- prompt;
- agent configuration;
- department tools;
- services;
- repositories;
- schemas;
- department-specific models.

### `rag/`

- file processing;
- chunking;
- embedding;
- Pinecone indexing;
- metadata filtering;
- retrieval.

### `realtime/`

- SSE connection handling;
- request event streams;
- publishing user-safe progress updates.

### `notifications/`

- persistent notifications;
- read/unread state;
- notification delivery through SSE.

### `onboarding/`

- spreadsheet upload;
- entity detection;
- field mapping;
- mapping confirmation;
- data import.

## 6.3 Standard Call Flow

For an API operation:

```text
FastAPI route
→ service
→ repository
→ SQLAlchemy
→ Neon PostgreSQL
```

For an agent tool:

```text
Department agent
→ tool
→ service
→ repository
→ SQLAlchemy
→ Neon PostgreSQL
```

## 6.4 Repository Layer

Use a light repository layer.

Repositories handle:

- SQLAlchemy queries;
- tenant scoping;
- persistence;
- reusable database access.

Services handle:

- business decisions;
- transactions;
- coordination;
- calling multiple repositories.

Avoid excessive repository interfaces and factories.

## 6.5 Transactions

Services control transactions.

One business operation may update several tables.

All related changes commit together or roll back together.

Repositories should not commit independently inside a multi-step business operation.

## 6.6 Tenant-Scoped Repositories

Every tenant-owned repository instance is created with the authenticated company ID.

```python
employee_repo = EmployeeRepository(
    session=session,
    company_id=current_user.company_id,
)
```

All reads, creates, updates, and deletes are automatically scoped to that company.

The company ID comes from trusted authentication context, not from a user-controlled request body.

## 6.7 Backend as Single Entry Point

The frontend never directly calls:

- Neon;
- Pinecone;
- the LLM provider.

All access goes through FastAPI.

## 6.8 Collaboration Runtime

`app.workflow.collaboration` owns action schemas, the explicit route registry, canonical
idempotency keys, runtime limits, and collaboration state transitions. Department-specific work
remains in department services and `DepartmentExecutionService`; collaboration orchestration does
not contain receiver business logic. Start, receiver-result, and return checkpoints use short
service-owned transactions. No transaction remains open across Pinecone or Groq calls.
