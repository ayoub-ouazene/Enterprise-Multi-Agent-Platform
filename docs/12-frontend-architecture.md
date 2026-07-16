# 12. Frontend Architecture

## 12.1 Stack

- React
- TypeScript
- feature-based frontend organization
- typed API client
- SSE client
- charting and visualization library

## 12.2 Main Application Areas

### Public / External

- company selection or company-specific entry point;
- Customer Support interface;
- external request tracking.

### Employee

- request submission;
- platform assistant;
- current requests;
- request tracking;
- notifications;
- profile.

### Department Manager

- department dashboard;
- requests requiring approval;
- requests requiring human action;
- request creation;
- department data tables;
- natural-language data editing;
- notifications.

### Company Account

- company onboarding;
- employee and manager imports;
- policy and document upload;
- mapping confirmation;
- company-wide data;
- failures;
- capability gaps;
- configuration.

## 12.3 Feature-Based Structure

```text
src/
├── app/
├── api/
├── auth/
├── companies/
├── requests/
├── notifications/
├── onboarding/
├── departments/
├── shared/
└── pages/
```

## 12.4 Request Tracking Page

The page may contain:

- Request ID;
- request summary;
- current owner department;
- current status;
- timeline;
- completed stages;
- current stage;
- safe explanations;
- decision-package cards;
- approval or action controls;
- final result;
- visualizations permitted for the current actor.

## 12.5 Natural-Language Data Editing

Authorized users can:

1. select a permitted entity or table;
2. write a natural-language change;
3. receive a structured preview;
4. confirm or cancel;
5. view the result.

The frontend must never send arbitrary SQL.

## 12.6 State Management

Use simple local or query-state tools first.

Do not add a large global state framework unless the application needs it.

Server data should be treated as backend-owned and refreshed through the API and SSE.
