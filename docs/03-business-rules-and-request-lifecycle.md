# 3. Business Rules and Request Lifecycle

## 3.1 One Owner Department

Every business request has exactly one owner department.

The owner remains responsible until the request reaches a terminal state.

Other departments are collaborators.

## 3.2 Router Clarification

The Router selects the owner department.

- High confidence: route immediately.
- Ambiguous request: ask clarification.
- Maximum clarification questions: three.
- If ambiguity remains, choose the most likely department or ask for a manual selection without starting an endless conversation.

## 3.3 Business Request vs Informational Question

Informational questions do not create a stored business request.

Examples:

- “What is the leave policy?”
- “How do I reset my password?”
- “What can this platform do?”

A business request is created when the interaction starts or modifies a company process.

Examples:

- vacation request;
- equipment request;
- software access;
- password reset requiring an operation;
- purchase request;
- technical incident;
- supplier search.

Ordinary conversation history is not permanently stored.

## 3.4 Unique Request ID

Every business request receives one unique Request ID.

All departments, tools, approvals, workflow events, failures, and notifications reference the same ID.

The platform does not create sub-requests.

## 3.5 Request Lifecycle

Every business request has a lifecycle.

Typical statuses:

- `created`
- `routing`
- `processing`
- `waiting_for_department`
- `waiting_for_human_approval`
- `waiting_for_human_action`
- `under_review`
- `completed`
- `rejected`
- `cancelled`
- `failed`

Request-type-specific stages may be more detailed.

## 3.6 Dynamic Planning

The owner department creates an initial high-level plan.

The plan is adaptive.

After tool results, department responses, reviewer feedback, human decisions, or new information, the agent may modify future steps.

Completed steps are not rewritten.

## 3.7 Information Acquisition Priority

Before asking the user, the department must check:

1. authenticated user identity;
2. company database;
3. company policies and RAG;
4. another department when appropriate;
5. the user only for information unavailable elsewhere.

The system must not ask users for data it already knows, such as company, employee ID, department, manager, or role.

## 3.8 AI Authority

The AI may answer or act independently when:

- the request is informational;
- the policy clearly defines the outcome;
- all required information is available;
- constraints can be deterministically checked;
- no human responsibility, financial spending, or physical action is required;
- an approved capability exists.

## 3.9 Human Approval and Action

Human involvement is required when:

- money is spent;
- physical stock is transferred;
- a physical task is required;
- vacation or another sensitive process requires managerial control;
- the situation is unusual or rare;
- policies conflict;
- confidence is insufficient;
- the action has significant consequences;
- legal or contractual responsibility exists;
- company policy explicitly requires approval.

Human approval is not a default step.

## 3.10 Minimum Human Effort

Before requesting human input, the AI must complete all possible:

- searching;
- reading;
- retrieval;
- comparison;
- calculation;
- constraint checking;
- evidence collection;
- summarization;
- recommendation preparation.

The human receives a decision package containing:

- concise request summary;
- relevant facts;
- completed checks;
- policy references;
- impact;
- AI recommendation;
- reason;
- confidence;
- exact action required.

## 3.11 Explainability

Every important approval, rejection, recommendation, escalation, failure, and capability gap includes a reason.

Reasons shown to users must respect visibility permissions.

## 3.12 Capability Gaps

Agents execute approved capabilities.

When no suitable capability exists:

1. do not invent an unsupported operation;
2. inform the user politely;
3. create a capability-gap record;
4. notify the relevant manager or Company account;
5. terminate the workflow gracefully.

## 3.13 Human Approval Strategy

Human approval uses a hybrid model.

Approval may be required by policy or requested by the agent because of unusual conditions, missing information, conflicting policy, low confidence, or high risk.

When the agent requests approval outside explicit policy, it must explain why.

## 3.14 Reviewer Rule

Important decisions may be sent to the Reviewer once.

The Reviewer provides feedback only.

The department agent revises once.

There is no second review loop.

If the revised result remains unsafe or uncertain, the workflow moves to human review or terminates.

## IT request flows

IT informational answers remain nonpersistent when immediate and grounded. Access, account,
hardware, and incident work uses the existing Request ID. Hardware inventory is checked before
purchase collaboration. Available assets produce assignment or delivery preparation; unavailable
stock produces Finance validation, with Procurement preparation allowed only after trusted Finance
validation state exists.
