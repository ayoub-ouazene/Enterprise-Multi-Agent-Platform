# 15. Failure Handling and Notifications

## 15.1 Failure Flow

```text
Failure
→ return to owner department agent
→ search for a valid alternative
→ continue if one exists
→ terminate if none exists
```

## 15.2 User Response

The user receives a polite general reason.

Do not expose:

- internal table names;
- SQL errors;
- stack traces;
- secrets;
- credentials;
- sensitive company details;
- raw model or tool errors.

## 15.3 Internal Failure Record

Internal records may include:

- Request ID;
- company ID;
- department;
- failure category;
- technical detail;
- failed tool or stage;
- timestamp;
- alternative attempted;
- resolution status.

## 15.4 Capability Gaps

When no approved capability exists:

- create a capability-gap record;
- notify the company or manager;
- explain safely to the user;
- terminate gracefully.

Capability gaps may track:

- department;
- requested operation;
- frequency;
- first seen;
- last seen;
- status.

## 15.5 Persistent Notifications

Use a database table for notifications that must remain until seen or handled.

Examples:

- approval required;
- human action assigned;
- request completed;
- request failed;
- capability gap detected;
- company action required.

## 15.6 Live Delivery

When the recipient is online, new notifications may be pushed through SSE.

The database remains the source of truth.

## 15.7 Retry Philosophy

Safe temporary failures may be retried a limited number of times.

Do not use endless retry loops.

Irreversible operations must avoid duplicate execution.
## Customer Support failures and escalation

Provider timeouts and transient failures use bounded retries; invalid structured output receives one
correction attempt within the configured retry limit. Persistent RAG, Groq, validation, or checkpoint
failures are sanitized and recorded through the existing failure service. Prepared human escalation
creates a manager-visible workflow event and notifies active Customer Support managers, falling back
to active Company accounts. No prompt, evidence text, credential, or complete provider payload is
logged.

## IT failures and notifications

IT Pinecone and Groq failures use bounded retries and sanitized RAG/LLM categories. Malformed output
uses the centralized correction policy and terminal failures use `FailureService`. Checkpoints
atomically persist the IT extension, request state, event, and applicable notification. Technician
preparation notifies an authorized IT manager or Company account without claiming execution.

## Finance failures and notifications

Finance Pinecone and Groq failures use bounded retries and sanitized RAG/LLM failure categories.
Malformed structured output receives one bounded correction attempt. Persistence, locking, or
provider failures use `FailureService`; insufficient balance, inactive periods, and currency mismatch
are business decisions and do not create failure logs. Approval preparation notifies an authorized
Finance manager or Company account. No prompt, raw evidence, credential, financial secret, or
provider payload is logged.

## Procurement failures and notifications

Procurement Pinecone and Groq failures use bounded retries and sanitized provider categories.
Malformed structured output receives one bounded correction attempt. Persistence and unexpected
execution failures use `FailureService`. Empty candidate sets, all-ineligible candidates, mixed
currencies, invalid weights, and Finance rejection are safe business outcomes rather than technical
failure logs. Unsupported external supplier discovery creates a capability gap only when discovery
is required. Human selection preparation notifies an authorized Procurement manager or Company
account without claiming that selection or purchase occurred. Prompts, raw evidence, quotation
contacts, credentials, and complete provider payloads are never logged.
