# Changelog

All notable changes to the Enterprise Multi-Agent Platform are documented in this file.

## [1.0.0] — 2026-07-27

### Frontend

- Authentication flow: public entry, company registration (signup), login, password change, password-force-change guard, logout
- Design system: CSS variable-based light/dark theme, semantic color tokens (neutral, primary, emerald, amber, warning, error, success, info), Tailwind custom utilities, font-scale system, spacing tokens, reduced-motion media query support, skip-link accessibility utility
- Layout system: AppShell, AdminShell, DepartmentShell with responsive mobile navigation, collapsible sidebar, skip-link navigation, and page max-width containers
- Theme system: Zustand-based theme store supporting auto (system preference), light, dark; persisted in localStorage; applies via <html> class and color-scheme
- Dashboard experience: role-specific dashboards (Company account, Employee, Department Manager, External user) with department navigation, activity panels, KPI cards, and quick action sections
- Business Requests: create request, requests list with status/attention filters, request detail with workflow timeline, event stream, status controls, and cancellation
- Human-in-the-Loop Actions: action history, decision package view, structured response forms, type-safe dismissal
- Onboarding & Self-Service: structured onboarding wizard (profile, departments, managers, employees, policies, optional data, review), import validation, department manager assignment
- Company Administration: 18 administration pages covering company profile, employee directory, departments, assets, software catalog, budgets, leave balances, holidays, staffing rules, suppliers, policies, managers, onboarding status
- Department Workspaces: specialized landing pages, overview with workload stats, request listing with relation/attention filters, human actions view, operations view, collaboration activity, and quick action panels
- Notifications page: grouped by date, read/unread filters, bulk read/unread controls, explicit action buttons; no automatic read-on-receive for SSE events
- Real-time updates: Server-Sent Events across requests, notifications, human-actions, admin tables, departments, and dashboard; targeted query invalidation; deep deduplication using seenEventIds
- Accessibility: aria-label and aria-live regions, role="alert" for errors, role="status" for loading, programmatic label/error linkage on all Input/Select/PasswordField components, focus trapping in Modal and ConfirmDialog, keyboard-navigable action items and tables
- API layer: typed request/response client, automatic token refresh on 401 (one attempt), secure sessionStorage token storage, consistent error normalization with human-friendly messages, no backend exception leaks to UI
- Responsive design: mobile-first with sm:/md:/lg:/xl: breakpoint classes, inline-style-count of 0 in production code, no hardcoded colors outside design tokens

### Backend

- FastAPI modular monolith with Pydantic v2 schemas
- Multi-tenant company isolation via dependency-injected repositories scoped to authenticated company
- Complete auth system: company registration, login, token refresh, password change, setup-authenticated-user dependency, force-change-password check
- Business request lifecycle: create, list, detail, cancel; per-request permission checks based on ownership and actor type
- Workflow engine: centralized LangGraph graph with nodes for router, department execution, collaboration start/receiver/return, reviewer, human action, completion, terminal failure; state versioned checkpoints using Pydantic state models; safe failure recording with tenant-scoped rollback
- Department execution: 5 predefined departments (Customer Support, HR, IT, Finance, Procurement) with structured contracts, tool constraints, safe output validation, and capability-gap routing
- Collaboration system: structured cross-department calls without sub-request creation, collaboration return stack, history, and idempotency checks
- Reviewer node: one independent feedback cycle support, revision attempt tracking, safe package summaries
- Human action node: requires department-manager or company-account authorization, decision package formulation, action-type and response tracking
- RAG / company knowledge: document upload, replace, retry ingestion, search; Pinecone vector store with tenant-scoped namespaces; chunking, extraction, and safe metadata filtering
- Admin API: CRUD endpoints for all 18 admin resources with company-scoped queries and optimistic lock patterns
- Department workspace API: stats, requests, actions, readiness, activity, operational records endpoints per department type with employee-scoped visibility
- Onboarding API: activation, status, manager coverage, manager candidates, department manager assignment, import validation/confirmation, templates
- Notifications API: list, unread count, mark read, mark all read, SSE stream
- Failure handling: capability-gap recording, terminal failure logging with safe-error propagation; no stack traces in API responses
- Real-time: SSE streams for request events and notifications with heartbeat, last-event-id replay, and permission-filtered visibility
- 590+ passing tests across all domains; FastAPI 0.139 compatibility fixes for _IncludedRouter route introspection

### Security & Compliance

- No tokens in localStorage (sessionStorage only)
- Tokens cleared on logout and session cleanup (queryClient.clear)
- Error normalization prevents backend exception exposure to clients
- No `is_staff` / `is_department_manager` frontend data reliance; backend enforces all authorization
- No dangerousSetInnerHTML usages in frontend code
- Prohibited-value scanning in workflow state (JWT, credentials, private keys, DB URLs)

### Fixes

- FastAPI 0.139 `_IncludedRouter` compatibility in test route introspection
- TypeScript strict null safety in department workspace pages
- Lucide icon `title` prop misuse fixed to native HTML title attribute
