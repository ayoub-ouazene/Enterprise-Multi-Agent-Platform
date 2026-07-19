# 7. LangGraph Workflow Architecture

## 7.1 One Centralized Graph

Version 1 uses one platform-level LangGraph graph.

The graph is not divided into department subgraphs.

Department code remains modular, but runtime orchestration is centralized.

## 7.2 Ownership

```text
workflow/
→ owns graph, state, nodes, routing, persistence, reviewer flow,
  human pauses, failures, and completion

departments/
→ own prompts, agents, tools, services, and repositories
```

## 7.3 Recommended Structure

```text
workflow/
├── graph.py
├── state.py
├── routing.py
├── persistence.py
└── nodes/
    ├── router.py
    ├── departments.py
    ├── reviewer.py
    ├── human_action.py
    ├── failure.py
    └── completion.py
```

## 7.4 Conceptual Graph

```mermaid
flowchart TD
    S[Start] --> R[Router / Platform Assistant]
    R --> D[Run Active Department]
    D --> X{Next Action}
    X -->|Tool| T[Execute Tool]
    X -->|Collaborate| C[Run Collaborating Department]
    X -->|Review| V[Reviewer]
    X -->|Human| H[Pause for Human]
    X -->|Finish| F[Complete Request]
    X -->|Failure| E[Failure Handler]
    T --> D
    C --> D
    V --> D
    H --> D
    E --> F
    F --> END[End]
```

## 7.5 Shared Workflow State

Use one state object organized into sections:

```python
class WorkflowState(TypedDict, total=False):
    request: dict
    planning: dict
    collaboration: dict
    execution: dict
    review: dict
    human_action: dict
    failure: dict
    result: dict
```

### Request Section

- Request ID
- Company ID
- Requester ID
- owner department
- active department
- request type
- current status
- original request summary

### Planning Section

- initial plan
- revised plan
- completed steps
- pending steps
- current step

### Collaboration Section

- current structured message
- collaborating department
- expected output
- latest collaboration result

Temporary collaboration messages are discarded when no longer needed.

### Execution Section

- relevant tool results
- important retrieved evidence references
- timestamps
- retry information

### Review Section

- review required
- package
- feedback
- feedback used
- revision completed

### Human Action Section

- required
- action type
- assigned user or manager
- decision package
- current status
- human response

### Failure Section

- failure type
- internal detail
- user-safe reason
- alternative attempted
- terminal decision

### Result Section

- decision
- reason
- final response
- completion metadata

## 7.6 Persistence

Persist business-critical state in PostgreSQL.

Do not persist:

- hidden chain of thought;
- raw prompts;
- unnecessary intermediate drafts;
- duplicated retrieval chunks;
- temporary formatting values.

Persist:

- lifecycle;
- plans;
- completed stages;
- important tool results;
- collaboration outcomes;
- review feedback;
- human action;
- failure;
- final result.

## 7.7 Pause and Resume

Human approval and action nodes pause workflow execution.

The request can resume later using its persisted state.

Backend restarts must not lose business-critical progress.

## 7.8 Adaptive Planning

Agents generate an initial high-level plan.

They may modify future steps after each important event.

The graph controls persistence and transitions; the agent decides appropriate next actions within policy and tool boundaries.
## Customer Support pause paths

The centralized graph supports three Step 13 Customer Support outcomes in addition to completion:
`wait_for_user_input` pauses for one clarification, collaboration prepares an IT diagnostic handoff,
and human action prepares an authorized escalation. These paths preserve the original Request ID,
owner department, and checkpointed state. They do not execute IT work or human actions.
