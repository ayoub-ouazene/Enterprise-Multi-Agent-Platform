# UAT Plan — Orchestra v1.0

## Scope
Functional acceptance of the five-department multi-agent platform before production launch.

## Environment
- **Frontend**: `https://app-staging.orchestra.example` (React + Vite)
- **Backend**: `https://api-staging.orchestra.example` (FastAPI)
- **Database**: Neon PostgreSQL staging
- **Vector Store**: Pinecone staging

## Test Accounts
| Role | Email | Password |
|------|-------|----------|
| Company Admin | `admin@acme.example` | `DemoPassword123!` |
| Employee | `emp001@acme.example` | `DemoPassword123!` |

## Test Scenarios

### 1. Authentication
- [ ] Login with valid credentials returns tokens.
- [ ] Login with invalid credentials shows safe generic error.
- [ ] Token refresh works silently before expiry.
- [ ] Change password validates current password and enforces 12-char minimum.
- [ ] Password change rejects mismatched confirmation.
- [ ] After password change, next login uses new password.

### 2. Navigation & Shell
- [ ] Sidebar links navigate correctly with React Router (no full reload).
- [ ] Header user menu toggles on click, closes on outside click / Escape.
- [ ] Mobile drawer opens/closes with slide animation.
- [ ] Theme toggle persists across sessions.

### 3. Requests
- [ ] Create a business request (any type).
- [ ] Request detail page shows correct Lucide timeline icons.
- [ ] Real-time SSE updates reflect workflow state changes.
- [ ] Cancel action works for `created`/`routing`/`processing` requests.
- [ ] Start/resume actions visible to managers only.

### 4. Departments
- [ ] Each of the 5 departments has a workspace page.
- [ ] Department stats display correctly.
- [ ] Readiness checks return accurate coverage.

### 5. Human Actions
- [ ] Pending actions appear in the list with correct status badges.
- [ ] Action detail page shows decision options.
- [ ] Submitting a decision updates action status.

### 6. Admin
- [ ] Employee directory search and filter work.
- [ ] Deactivate employee triggers confirmation dialog with animation.
- [ ] Import validation shows row-level errors.
- [ ] Admin overview stats match database counts.

### 7. Assistant
- [ ] Send a message to the platform assistant.
- [ ] Router category classification returned in response.
- [ ] Clarification question rendered when `needs_clarification=true`.

### 8. Notifications
- [ ] Notification bell badge updates on new events.
- [ ] Mark-read updates UI instantly.
- [ ] Old notifications load via pagination.

### 9. RAG / Knowledge
- [ ] Document upload initiates processing.
- [ ] Vector search returns semantically relevant chunks.

### 10. Failure Handling
- [ ] Capability gap list loads with filters.
- [ ] Updating gap status reflects immediately.

## Regression
- [ ] Full build passes `npm run build` with zero errors.
- [ ] Backend `pytest` suite passes (27+ tests).
- [ ] Lighthouse accessibility score ≥ 90.

## Sign-off Criteria
All critical-path checkboxes must pass before launch.
