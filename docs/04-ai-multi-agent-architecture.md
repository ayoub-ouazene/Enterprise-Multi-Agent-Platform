# 4. AI and Multi-Agent Architecture

## 4.1 Logical Agents

The system contains:

- Router / Platform Assistant;
- Customer Support agent;
- HR agent;
- IT agent;
- Finance agent;
- Procurement agent;
- one shared Reviewer agent.

Agents may share the same LLM provider, model, and API key.

Each logical agent has its own:

- system prompt;
- responsibilities;
- boundaries;
- tools;
- permissions;
- RAG filters;
- structured output schemas;
- collaboration behavior.

## 4.2 Router / Platform Assistant

The Router:

- answers platform-related questions;
- explains how to use the system;
- helps users formulate requests;
- identifies informational questions;
- identifies business requests;
- selects the owner department;
- asks up to three clarification questions.

The Router never performs department-specific business operations.

## 4.3 Department Agent Processing

A department agent can dynamically decide:

- what information is needed;
- what policies to retrieve;
- what tools to call;
- what other departments to involve;
- what steps can run in parallel;
- whether reviewer feedback is needed;
- whether human approval or action is needed;
- how the plan changes after new information.

Mandatory checks are applied when relevant.

## 4.4 Stateless Agents

Department agents do not keep persistent local memory.

Historical information is retrieved from:

- PostgreSQL;
- Pinecone;
- active request state;
- collaborating departments.

The company remembers; the agents reason.

## 4.5 Structured Communication

Agent-to-agent communication uses structured business objects.

Example:

```json
{
  "request_id": "REQ-1245",
  "sender_department": "it",
  "receiver_department": "finance",
  "action": "validate_budget",
  "payload": {
    "item_type": "monitor",
    "estimated_cost": 300
  },
  "expected_output": {
    "decision": "approved_or_rejected",
    "reason": "string"
  }
}
```

Temporary messages exist only in the active workflow state.

Meaningful results may be persisted as workflow events.

## 4.6 Business Rules

Business rules use a hybrid model.

### Mostly RAG

Used for:

- policies;
- procedures;
- eligibility descriptions;
- internal rules;
- guidelines;
- approval conditions;
- department manuals.

### Executable tools

Used for:

- calculations;
- database queries;
- constraint checks;
- inventory checks;
- budget checks;
- database updates;
- account operations;
- asset assignment.

## 4.7 Reviewer Agent

The Reviewer receives a structured review package, not the entire raw execution history.

The package includes:

- request summary;
- proposed decision;
- relevant policies;
- evidence;
- tool results;
- checked constraints;
- required approvals;
- explanation;
- confidence.

The Reviewer returns feedback.

It cannot directly change the decision.

## 4.8 Tool Access

Each department agent receives its own approved tool set.

There is no separate Tool Selector in Version 1.

Tools validate their own inputs and normal backend constraints.

The architecture does not introduce an extra validation agent.

## 4.9 Failure Feedback

Tool, retrieval, and department failures return to the owner department agent.

The agent may try a valid alternative.

If no alternative exists, it produces a safe user-facing response and terminates.
## Customer Support model policy

Customer Support always starts with the configured Fast Groq model. A validated Fast result may
trigger at most one Reasoning-model pass when deterministic signals identify a complex technical
issue, conflicting evidence, low confidence, material risk, or a prepared IT/human handoff. The
agent uses strict structured output and cannot select arbitrary model identifiers.

## IT model and tool policy

IT uses only configured Fast and Reasoning Groq roles. Simple questions, extraction, access
preparation, and known incidents use Fast. Complex incidents, conflicting evidence, higher-risk
access, and purchase-collaboration decisions use Reasoning. Tools are limited to read-only
`check_asset_inventory` and `check_software_availability`; arbitrary tools, SQL, shell,
identity-provider, physical, and purchasing operations are prohibited.
