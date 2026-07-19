# 10. API Architecture

## 10.1 Principles

- All endpoints are served by FastAPI.
- Use typed Pydantic request and response schemas.
- Tenant context comes from authentication.
- Do not accept trusted `company_id` from normal client payloads.
- Separate read permissions from write permissions.
- Business workflows return a Request ID.
- Live progress is delivered through SSE.

## 10.2 API Groups

### Authentication

```text
/api/v1/auth
```

Examples:

- sign in;
- refresh token;
- current user;
- sign out.

### Companies

```text
/api/v1/companies
```

Examples:

- register company;
- get company profile;
- update configuration;
- upload onboarding data;
- confirm import mapping.

### Users and Employees

```text
/api/v1/users
/api/v1/employees
```

Examples:

- list permitted employees;
- retrieve employee profile;
- update permitted fields;
- manager assignment.

### Business Requests

```text
/api/v1/requests
```

Examples:

- submit request;
- list current user's requests;
- get request details;
- cancel request when allowed;
- provide requested information;
- list manager department requests.

### Request Actions

```text
/api/v1/requests/{request_id}/actions
```

Examples:

- approve;
- reject;
- confirm human action;
- provide missing information.

### Live Events

```text
/api/v1/requests/{request_id}/events
```

SSE endpoint for live updates.

### Notifications

```text
/api/v1/notifications
```

Examples:

- list notifications;
- mark read;
- retrieve unread count.

### Documents and Knowledge

```text
/api/v1/documents
```

Examples:

- upload document;
- list company documents;
- replace policy version;
- inspect ingestion status.

### Company Data Management

```text
/api/v1/company-data
```

Examples:

- list permitted tables or entities;
- preview natural-language edit;
- confirm edit.

### Department Data

Feature-specific endpoints may exist for:

- assets;
- budgets;
- suppliers;
- leave balances;
- software catalog.

They remain permission-controlled.

## 10.3 Request Submission

A business-request endpoint should:

1. authenticate user;
2. derive company context;
3. validate basic input;
4. create Request ID;
5. persist initial state;
6. start workflow execution;
7. return Request ID and tracking URL.

## 10.4 Informational Questions

Informational questions may use a synchronous endpoint and return an immediate answer when no business request is created.

## 10.5 Errors

User-facing errors should be safe and general.

Internal error details go to logs and failure records.

## 10.6 Idempotency

Important mutation endpoints should support idempotent behavior where repeated requests could cause duplicate operations, especially approvals and financial confirmations.

## 10.7 IT API Surface

Step 14 adds no direct IT execution endpoint. IT remains available through
`POST /api/v1/assistant/message` and existing request workflow start/resume endpoints. Asset and
software imports/writes remain later onboarding work. Normal users cannot directly invoke asset
assignment, password reset, account unlock, supplier, budget, or purchase operations.
