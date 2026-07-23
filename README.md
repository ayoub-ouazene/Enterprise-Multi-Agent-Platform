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

## Architecture overview

### Frontend

- React + TypeScript
- Vite-based client application
- Feature-based page and API organization
- Typed API layer and SSE-based live updates

### Backend

- Python + FastAPI
- Pydantic schemas and typed API contracts
- SQLAlchemy 2.0 with Alembic migrations
- Modular monolith structure organized by domain

### Workflow and AI orchestration

- LangGraph for request orchestration and workflow state
- LangChain where useful for LLM integration and orchestration helpers
- Department-specific agents with structured outputs and tool constraints
- Reviewer and collaboration flow support

### Data and knowledge layer

- PostgreSQL for relational business data
- Pinecone for vector-based company knowledge retrieval
- Tenant-scoped repositories and service-layer business rules

## Repository structure

- backend/: FastAPI application, Alembic migrations, domain modules, and tests
- frontend/: React + TypeScript UI and API hooks
- docs/: the authoritative product specification and architecture documents

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
