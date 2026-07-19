# 8. Database Architecture

## 8.1 General Model

Use one hosted PostgreSQL database and one unified schema for all companies.

Do not create a separate database or duplicate tables for every company.

Every tenant-owned table includes `company_id`.

## 8.2 Data Categories

### Core Platform Tables

- `companies`
- `users`
- `departments`
- `employees`
- `business_requests`
- `workflow_events`
- `human_actions`
- `notifications`
- `capability_gaps`
- `failure_logs`

### HR Tables

- `leave_balances`
- `leave_requests`

No dedicated onboarding table in Version 1.

### IT Tables

- `assets`
- `software_catalog`
- `software_licenses`
- `access_requests`
- `it_incidents`
- `hardware_requests` when structured request data requires it

### Finance Tables

- `budgets`
- `purchase_requests`
- `financial_transactions`

No separate general `expenses` table in Version 1. Purchase-related financial data remains attached to the purchase request, while confirmed budget movements are recorded in `financial_transactions`.

### Procurement Tables

- `suppliers`
- `supplier_candidates`

A separate supplier-evaluations table is unnecessary in Version 1. Candidate rows contain price, delivery, scores, ranking, and recommendation reason.

### Customer Support Tables

- `support_issues` only when a real issue becomes a business request.

Ordinary Customer Support Q&A is not persisted as a business request.

## 8.3 Request Extension Pattern

Common information belongs in `business_requests`.

Specialized information belongs in a request-specific extension table.

Example:

```text
business_requests
└── leave_requests
```

```text
business_requests
└── hardware_requests
```

```text
business_requests
└── purchase_requests
```

The extension row uses the same Request ID.

This is not a sub-request.

## 8.4 Core Request Fields

Expected common fields include:

- ID / Request ID
- company ID
- requester user ID
- owner department
- active department
- request type
- status
- current stage
- summary
- final decision
- final reason
- workflow-state JSONB
- custom data JSONB where required
- created timestamp
- updated timestamp
- completed timestamp

## 8.5 Workflow Events

`workflow_events` store meaningful persistent progress events, such as:

- request created;
- routed to IT;
- inventory check completed;
- Finance validation completed;
- waiting for approval;
- request completed.

Do not use workflow events to store all internal department JSON messages.

## 8.6 Temporary Department Messages

Inter-department messages are temporary workflow variables.

They may exist in memory or persisted workflow checkpoints while active.

They are discarded when no longer needed.

Only meaningful outcomes are persisted.

## 8.7 Review Storage

No separate reviews table.

Store reviewer data in request-related workflow-state JSONB:

- required;
- status;
- feedback;
- reviewed timestamp;
- revision completed.

## 8.8 Notifications

Use a dedicated `notifications` table because notifications must survive logout and page refresh.

Typical fields:

- ID
- company ID
- recipient user ID
- Request ID
- type
- title
- message
- read flag
- created timestamp
- read timestamp

## 8.9 Financial Transactions

`financial_transactions` records confirmed changes to a budget.

A transaction is created only after required human approval and confirmed financial action.

It provides traceability for how a budget changed.

## 8.10 Standard Columns vs Custom Data

Frequently queried and important fields use normal relational columns.

Company-specific extra fields use JSONB `custom_data`.

Do not store the entire domain model in JSONB.

## 8.11 Tenant Isolation

Repository queries automatically apply `company_id`.

Creates automatically assign the repository company ID.

Updates and deletes include the company filter.

Cross-company record IDs must behave as not found.
## Customer Support extension

`support_issues` is a tenant-owned one-to-one extension of `business_requests`; its `request_id` is
both the primary key and a cascading foreign key. It stores issue category/status, product or
service, symptoms, error messages, structured troubleshooting progress, resolution, escalation
flags, safe custom state, and timestamps. Repository access always includes `company_id`.

## IT foundation tables

`access_requests`, `hardware_requests`, and `it_incidents` are one-to-one extensions using the
original Request ID. `assets` and `software_catalog` are tenant-owned reference data. Important
status, type, employee, reporter, and active fields are relational columns; safe optional company
fields remain JSONB. Password, reset-token, supplier, budget, purchase, and physical-execution data
is not stored by this foundation.
