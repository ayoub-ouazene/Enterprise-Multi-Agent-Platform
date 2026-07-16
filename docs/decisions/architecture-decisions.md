# Accepted Architecture Decisions

## ADR-001 — Supported Departments

Version 1 supports Customer Support, HR, IT, Finance, and Procurement only.

## ADR-002 — One Owner Department

Every business request has exactly one owner department.

## ADR-003 — No Sub-Requests

Collaborating departments use the same Request ID.

## ADR-004 — Router as Platform Assistant

The Router also answers platform-related questions and may ask at most three clarification questions.

## ADR-005 — Shared Database Multi-Tenancy

All companies use one PostgreSQL schema with `company_id` tenant scoping.

## ADR-006 — Approved Capabilities

Known operations use approved tools. Unsupported operations create capability gaps and terminate gracefully.

## ADR-007 — Request Persistence

Only business requests are persisted. Ordinary Q&A and general conversation history are not permanently stored.

## ADR-008 — Request Lifecycle

Every business request has persistent state and a lifecycle.

## ADR-009 — Structured Agent Communication

Departments exchange structured objects, not free-form natural-language messages.

## ADR-010 — RAG-First Business Rules

Most policies and rules are retrieved. Calculation, validation, and mutation use tools.

## ADR-011 — Explainability

Important decisions include reasons.

## ADR-012 — Autonomous Collaboration

The owner department may invoke collaborators without returning to the Router.

## ADR-013 — Actor Types

Actors are Company account, external user, employee, and department manager.

## ADR-014 — Spreadsheet Onboarding

Version 1 imports company spreadsheets using intelligent mapping and mandatory company confirmation.

## ADR-015 — Natural-Language Data Editing

Authorized managers and the Company account may request permitted data edits through natural language with preview and confirmation.

## ADR-016 — Hybrid Human Approval

Policy may require approval, and agents may request approval for unusual, risky, conflicting, or uncertain cases.

## ADR-017 — Minimum Human Effort

Agents complete all automatable analysis before requesting a minimal human decision or action.

## ADR-018 — Department as Mini-System

Departments have independent configurations, prompts, tools, policies, and permissions.

## ADR-019 — Flexible Department Internals

Departments share a common external behavior but may contain different internal resources.

## ADR-020 — Internal Information Acquisition

Agents query identity, database, RAG, and other departments before asking the user.

## ADR-021 — Dynamic Planning

Agents create a high-level plan and may revise future steps.

## ADR-022 — External Workflow State

Workflow state is stored outside the LLM.

## ADR-023 — Selective Reviewer

Important decisions may receive one independent feedback-and-revision cycle.

## ADR-024 — Stateless Agents

Agents retrieve history from system data rather than local persistent memory.

## ADR-025 — Direct Department Tool Access

No Tool Selector agent in Version 1.

## ADR-026 — Company Knowledge Organization

One logical company knowledge base with department metadata filters.

## ADR-027 — Modular Monolith

Version 1 uses one FastAPI modular monolith.

## ADR-028 — Feature-Based Code Structure

Backend modules are organized by business feature.

## ADR-029 — Light Repositories

Services use light repositories for database access.

## ADR-030 — Service Transactions

Services control commit and rollback.

## ADR-031 — Automatic Tenant Repository Scope

Repositories automatically filter all tenant-owned operations by authenticated company ID.

## ADR-032 — One Centralized LangGraph

Version 1 uses one graph; department subgraphs are not used.

## ADR-033 — Central Workflow Ownership

The workflow module owns LangGraph nodes and orchestration.

## ADR-034 — Structured Shared Workflow State

One workflow state is organized into logical sections.

## ADR-035 — Persistent Business State

Business-critical workflow state is persisted; model internals are not.

## ADR-036 — Hosted Stack

Use React, TypeScript, FastAPI, LangGraph, Neon PostgreSQL, Pinecone, SQLAlchemy, and Alembic.

## ADR-037 — Backend Single Entry Point

The frontend never directly calls the LLM, relational database, or vector database.

## ADR-038 — SSE Real-Time Tracking

Live backend-to-frontend request updates use Server-Sent Events.

## ADR-039 — Role-Based Information Visibility

Actors see only normally authorized workflow information.

## ADR-040 — Request Extension Tables

Common request information is stored in `business_requests`; specialized data uses extension tables with the same Request ID.

## ADR-041 — Temporary Department Messages

Inter-department messages are not permanently stored.

## ADR-042 — No Reviews Table

Reviewer data remains in workflow-state JSONB.

## ADR-043 — Persistent Notifications

Notifications remain stored until seen or handled.

## ADR-044 — No Onboarding Table

Onboarding uses a request, workflow state, and updates to other domain records.

## ADR-045 — Financial Transactions

Confirmed budget movements are recorded in a simple financial transaction ledger.

## ADR-046 — One Supplier Candidate Table

Candidate and evaluation data are stored together in `supplier_candidates`.
