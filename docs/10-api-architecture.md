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

The list and detail responses are safe frontend projections. They expose user-facing
state summaries, authorized department identity, attention indicators, connected
HumanAction summaries, allowed actions, and sanitized final results where applicable.
They do not expose workflow JSONB, collaboration payloads, Reviewer packages, decision
packages, provider details, or other internal execution state. Request filtering
(including search, status, owner department, request type, attention, date range, and
authorized requester scope) is performed by the backend.

### Request Actions

```text
/api/v1/requests/{request_id}/actions
```

Examples:

- approve;
- reject;
- confirm human action;
- provide missing information.

### HumanActions

```text
/api/v1/human-actions
/api/v1/human-actions/{action_id}
/api/v1/human-actions/{action_id}/submit
```

Inbox responses are bounded summaries and never include decision-package or response JSONB.
Authorized detail responses contain only an action-type allowlisted context, safe related-request
summary, allowed decisions, and bounded history. Submission validates the decision against the
action type and may include the last observed update timestamp so stale or concurrently resolved
actions fail without overwriting the authoritative decision.

### Live Events

```text
/api/v1/requests/{request_id}/events
```

SSE endpoint for live updates.

The REST timeline returns only persisted events visible to the authenticated actor,
with a safe title, message, actor label, optional department reference, sequence
number, and timestamp. Internal stage names and event payloads are not part of the
public timeline response. SSE is a change signal; clients reload the relevant REST
projection and do not treat streamed payloads as authoritative state.

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

## 10.8 Finance API Surface

Finance execution remains available only through `POST /api/v1/assistant/message` and existing
request workflow start/resume endpoints. Read-only management endpoints are `GET /api/v1/budgets`,
`GET /api/v1/budgets/{budget_id}`, `GET /api/v1/financial-transactions`, and
`GET /api/v1/financial-transactions/{transaction_id}`. Company accounts and Finance managers may
read company financial records; other department managers may read only their department budget
summary. Employees and external users cannot list full financial data. No public financial mutation
endpoint exists.

## 10.9 Procurement API Surface

Procurement execution remains available only through the assistant and workflow APIs. Authorized
read endpoints expose a Procurement request, its safe candidate list, or one candidate. Company
accounts and active Procurement managers may create and update request-scoped candidates;
authorized collaborating department managers may read only the relevant shortlist. Employees and
external users cannot mutate candidates. No public endpoint executes Procurement, selects a final
supplier, creates a purchase order, pays a supplier, or signs a contract.

## 10.10 HR API Surface

HR executes through assistant/workflow APIs. Read-only endpoints expose an employee's own data and
narrowly authorized leave, onboarding, and job-description records. Direct managers, HR managers,
and Company accounts receive only permitted tenant scope. External users have no HR access, and no
public HR mutation endpoint exists.

## 10.11 Collaboration API Surface

There is no public collaboration mutation endpoint. Clients cannot submit a company, sender,
receiver, action, owner, active department, depth, or return target. Collaboration runs only from a
trusted department result inside the existing assistant and request-workflow APIs. Authorized
timeline APIs expose sanitized meaningful events rather than temporary collaboration payloads.

## 10.12 Company Onboarding API Surface

An authenticated, inactive Company account may use the restricted onboarding surface without
receiving access to the normal operational application. The backend checklist at
`GET /api/v1/onboarding/status` is authoritative for readiness and activation.

The wizard uses the tenant-scoped Company profile and fixed-department administration endpoints,
the controlled employee import validate/confirm flow, and the existing knowledge-document
ingestion API. Manager assignment uses:

- `GET /api/v1/onboarding/manager-coverage`;
- `GET /api/v1/onboarding/manager-candidates`, bounded and filtered to active same-company
  employees in the selected department;
- `POST /api/v1/onboarding/departments/{department_id}/manager`.

Import validation responses expose only allowlisted preview fields and password-state indicators.
They never return submitted passwords, password hashes, complete source rows, or unrestricted
validation JSON. `POST /api/v1/onboarding/activate` revalidates every blocking requirement before
activating the Company.

## 10.13 Company Administration API Surface

The authenticated administration workspace uses explicit tenant-scoped resources under
`/api/v1/admin`. Company accounts receive the approved full administration surface. Department
managers receive only the resource and department scope explicitly allowed for their department;
employees and external users are rejected by backend dependencies even if they navigate directly
to an administration URL.

The surface covers Company profile, employees, fixed departments, IT assets and software,
Finance budgets, Procurement suppliers, HR holidays and staffing rules. Employee responses expose
safe account-state fields but never password hashes or credentials. Selectors use bounded
same-company employee searches rather than loading an unrestricted directory.

High-impact mutations are server-authoritative:

- employee termination uses the deactivation operation, which checks manager coverage, assigned
  assets, and pending HumanActions;
- department disabling is rejected while active members remain;
- asset assignment requires an active same-company employee, and retirement requires prior
  unassignment;
- software capacity and budget changes preserve backend concurrency and balance validation;
- duplicate holiday dates and overlapping active staffing periods return conflicts.

Budget amounts remain decimal strings in the API. The frontend does not calculate authoritative
balances, grant software access, perform physical asset delivery, select suppliers, or rewrite
historical leave outcomes. Administration SSE messages are change signals that invalidate only
the affected query families; REST responses remain authoritative.
