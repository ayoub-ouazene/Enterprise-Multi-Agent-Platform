# 11. Real-Time Request Tracking

## 11.1 Technology

Use Server-Sent Events.

SSE provides live backend-to-frontend updates without page refresh.

## 11.2 Communication Pattern

```text
Backend → Frontend:
SSE status and notification events

Frontend → Backend:
Normal HTTP actions
```

## 11.3 Request Page Behavior

The page initially loads the persisted request state through HTTP.

It then opens an SSE stream for new events.

If the page refreshes, the persisted state is loaded again and the stream resumes from the current point.

## 11.4 Event Types

Examples:

- `request.created`
- `request.routed`
- `step.started`
- `step.completed`
- `department.changed`
- `review.required`
- `human.approval_required`
- `human.action_required`
- `request.completed`
- `request.rejected`
- `request.failed`
- `notification.created`

## 11.5 Visibility

Event payloads must be role-aware.

### Employee / External User

May see:

- public status;
- current general stage;
- completed public stages;
- required user actions;
- final result;
- safe failure reason.

### Manager

May additionally see:

- evidence summaries;
- policy checks;
- recommendation;
- relevant budget or operational effects;
- approval controls.

### Company Account

May additionally see:

- capability gaps;
- internal failures;
- company-wide monitoring;
- configuration problems.

## 11.6 Hidden Information

Do not stream:

- prompts;
- hidden reasoning;
- credentials;
- unrestricted raw tool output;
- confidential records outside the user's role;
- another company's data.

## 11.7 Reliability

SSE is a live delivery channel, not the source of truth.

PostgreSQL stores the authoritative request state.

If an event is missed, the frontend reloads current state.
