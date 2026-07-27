# Enterprise Multi-Agent Platform

This repository contains a generalized, multi-tenant enterprise web platform for AI-powered business operations. The product is designed to help organizations route internal and external requests through specialized departments, use company knowledge safely, collaborate across teams when needed, and keep human approvals and actions limited to the moments where they are truly required.

## What this platform is building

The system supports a shared platform experience for companies that need:

- intelligent department agents for everyday enterprise workflows;
- tenant-aware business request handling;
- policy and document retrieval through RAG;
- deterministic workflow execution with human checkpoints;
- live progress tracking for submitted requests;
- onboarding and company-data import flows.

## Supported departments

Version 1 is structured around five predefined departments:

- Customer Support
- Human Resources
- Information Technology
- Finance
- Procurement

Each department has its own prompt, boundaries, tool access, permissions, and collaboration behavior, while sharing the same platform workflow and request lifecycle.

## Core product capabilities

- Multi-tenant company isolation and scoped access control
- Business request creation, routing, status tracking, and completion
- Department collaboration without creating sub-requests
- RAG-powered answers grounded in company documents and policies
- Safe human approval and human-action checkpoints
- Live request updates through Server-Sent Events
- Failure handling, notifications, and capability-gap reporting
- Company onboarding and structured data import flows

## What's included (v1)

### Frontend

- React + TypeScript with Vite, Tailwind CSS, and Framer Motion
- Comprehensive design system with CSS variable theming and reduced-motion support
- Public entry: landing page, company registration, login, password change, password-force-change guard, logout
- Role-based dashboards (Company account, Employee, Department Manager, External user)
- Business request creation, list, detail, status filtering, workflow timeline, and cancellation
- Human-in-the-Loop Actions: history, decision packaging, structured response forms
- Onboarding wizard with validation summaries, import flows, and activation
- Department workspaces (5 departments) with workload metrics, request relations, human actions, operations, and collaboration activity
- Company administration (18 CRUD pages): company profile, employee directory, departments, assets, software catalog, budgets, leave balances, holidays, staffing rules, suppliers, policies, manager assignment, onboarding status
- Notifications page with grouped unread/read view, explicit read controls (no toast library)
- Real-time updates via Server-Sent Events with deduplication and targeted query invalidation
- Accessibility: skip-link navigation, focus trapping in modals, aria-live regions, programmatic label/error linkages, keyboard-navigable tables
- Safe error handling: normalized errors with human-friendly messages, no backend exception leakage

### Backend

- Python + FastAPI modular monolith with Pydantic v2 schemas and SQLAlchemy 2.0
- Full auth system: company registration, login, token refresh, password change
- Workflow engine: centralized LangGraph graph with router, department execution, collaboration (start/receiver/return), reviewer, human action, completion, and terminal failure nodes
- State persistence using versioned Pydantic checkpoints with tenant-scoped rollback
- 5 department agents with structured contracts, tool constraints, safe output validation, and capability-gap routing
- Reviewer node with one independent feedback cycle and revision tracking
- Human action node with manager/company-account authorization and decision packaging
- RAG: document upload, replace, retry ingestion, search; Pinecone vector store with tenant-scoped namespaces
- Admin API (18 resources), department workspace API, onboarding API, notifications API
- SSE streams for request events and notifications with heartbeat and last-event-id replay
- 590+ passing tests across all domains

## Repository structure

- `backend/`: FastAPI application, Alembic migrations, domain modules, and tests
- `frontend/`: React + TypeScript UI and API hooks
- `docs/`: the authoritative product specification and architecture documents

## Documentation

The full system specification and implementation guidance live in the docs directory.

Recommended reading order:

1. docs/01-system-overview.md
2. docs/02-actors-and-departments.md
3. docs/03-business-rules-and-request-lifecycle.md
4. docs/04-ai-multi-agent-architecture.md
5. docs/05-technology-stack.md
6. docs/06-backend-architecture.md
7. docs/07-langgraph-workflow-architecture.md
8. docs/08-database-architecture.md
9. docs/09-rag-company-knowledge.md
10. docs/10-api-architecture.md
11. docs/11-realtime-request-tracking.md
12. docs/12-frontend-architecture.md
13. docs/13-company-onboarding-data-import.md
14. docs/14-auth-permissions-multitenancy.md
15. docs/15-failure-handling-notifications.md
16. docs/16-deployment-architecture.md
17. docs/17-future-improvements.md
18. docs/18-codex-implementation-instructions.md

The architecture decisions are summarized in docs/decisions/architecture-decisions.md.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the version history.

## Local development entry flow

Use the existing Conda environment for the backend:

```powershell
cd backend
conda run -n dev python -m alembic upgrade head
conda run -n dev python -m uvicorn app.main:app --reload
```

In a second terminal, use the committed frontend lock file:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173/`. A Company account can register publicly and is then directed through onboarding before activation. Employees and department managers are provisioned by a Company account, while external users use the approved provisioning flow; those roles do not have unrestricted public signup.

The frontend reads `VITE_API_BASE_URL` (default `http://127.0.0.1:8000/api/v1`) from `frontend/.env`. The backend reads allowed origins from `CORS_ORIGINS` in `backend/.env`; keep this list restricted to the actual frontend origins.

For local development data, the interactive seed command creates no fixed password and is blocked outside development/test environments:

```powershell
cd backend
conda run -n dev python scripts/seed_demo.py
```
