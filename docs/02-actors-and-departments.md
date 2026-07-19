# 2. Actors and Departments

## 2.1 Actor Types

### Company Account

Represents the organization using the platform.

Capabilities include:

- company registration and configuration;
- uploading company spreadsheets and documents;
- confirming data mappings during onboarding;
- viewing company-wide data;
- receiving capability-gap and failure notifications;
- managing employees and department managers;
- editing permitted data through natural-language instructions;
- monitoring all company requests according to authorization rules.

### External User

Represents a customer or client of a registered company.

Main interactions:

- customer questions;
- product or service explanations;
- troubleshooting;
- FAQ and RAG-based answers;
- reporting technical issues;
- tracking their own customer-support requests.

### Employee

Represents an internal company worker.

Employees may:

- ask policy questions;
- submit business requests;
- track their requests live;
- provide information only when it cannot be obtained internally;
- approve or confirm actions only when their role permits it.

### Department Manager

A manager is an employee with authority inside a department.

Managers may:

- create requests;
- create requests for their own department;
- receive requests from another department or manager;
- monitor department requests;
- approve or reject where required;
- confirm physical or administrative human actions;
- provide missing information;
- view detailed decision packages;
- view and edit permitted department data.

## 2.2 Department Model

A department is a mini-system, not only a prompt.

A department may contain:

- a specialized LLM agent configuration;
- a system prompt;
- company-specific RAG access;
- approved tools;
- services and repositories;
- permissions;
- policies and business rules;
- collaboration behavior;
- human-action conditions.

Departments expose the same general behavior externally:

1. receive a request;
2. process it;
3. collaborate when needed;
4. return a structured result.

Internally, departments may have different resources and logic.

## 2.3 Customer Support

### Scope

Customer Support primarily answers external-user questions and prepares unresolved technical issues for IT or human support.

Supported areas:

- customer questions;
- product and service explanations;
- troubleshooting;
- FAQ and RAG-based answers;
- escalation to human support;
- issue diagnosis and structured ticket preparation.

### Boundaries

- It may explain refund, return, warranty, or complaint policies.
- It does not execute refunds or modify customer financial records in Version 1.
- Generic customer-information integrations such as shipment tracking or subscription management are not core Version 1 capabilities.
- Ordinary Q&A is not persisted as a business request.
- A business request is created only when a real issue or process is initiated.

### Issue Diagnosis and Ticket Preparation

Customer Support may:

- understand the external problem;
- retrieve troubleshooting guidance;
- ask only necessary questions;
- summarize symptoms and attempted solutions;
- classify the issue;
- prepare structured technical information;
- forward the same request to IT when technical handling is required.

## 2.4 Human Resources

Supported areas:

- employee policy questions;
- leave and vacation requests;
- onboarding guidance;
- internal rules;
- benefits explanations;
- job-description generation.

### Leave Requests

Leave handling is end-to-end except where human approval is required.

The HR agent may:

- retrieve leave policy;
- verify remaining leave balance;
- evaluate minimum staffing constraints;
- inspect overlapping approved leave;
- check company constraints;
- request manager approval;
- update leave-related records after approval;
- provide an explanation for approval or rejection.

Recruitment is postponed because it is a large independent product area and is not essential for Version 1.

Onboarding does not require a dedicated onboarding table. It is represented by a business request, workflow state, and updates to employee, account, access, and asset records.

## 2.5 Information Technology

Supported areas:

- software-access requests;
- account creation and access changes;
- password reset and account unlock workflows;
- MFA or identity-related operations;
- hardware requests;
- inventory checks;
- asset assignment;
- software installation requests;
- incident diagnosis and coordination;
- employee hardware issues.

### Hardware Requests

IT is normally the owner of equipment requests.

The IT agent may:

- verify employee eligibility;
- retrieve relevant policy;
- inspect current assigned assets;
- inspect stock availability;
- reserve or assign available assets when allowed;
- request Finance validation when purchase is needed;
- request Procurement supplier research;
- prepare a human action for physical delivery;
- update inventory and assignment records after confirmation.

### Incident Management

The AI performs diagnosis, research, summarization, prioritization, and coordination.

Human technicians perform physical repairs or actions when necessary.

## 2.6 Finance

Finance provides financial governance.

Supported areas:

- purchase-request validation;
- budget checks;
- financial-policy checks;
- expense or reimbursement requests where later implemented;
- budget monitoring;
- final price validation after Procurement returns candidates;
- financial summaries and reports according to permissions.

Finance collaborates with IT and Procurement in purchase workflows.

Spending money requires human approval.

Only confirmed financial movements affect budgets and create financial transaction records.

## 2.7 Procurement

Procurement is limited to decision support in Version 1.

Its workflow ends after generating ranked suppliers or purchase candidates.

It may:

- understand purchase specifications;
- search approved or external suppliers;
- compare price, delivery, reliability, quality, and other criteria;
- rank candidates;
- explain the ranking;
- return the candidate list to the owner department or Finance.

It does not execute the purchase.

A human performs the final purchase action.

## 2.8 Department Collaboration

The owner department may invoke another department without asking the Router or user.

Examples:

- Customer Support → IT for an external technical issue.
- IT → Finance for budget validation.
- Finance → Procurement for supplier research.
- Procurement → Finance with ranked candidates and prices.
- HR → IT during employee onboarding.
- IT → HR when employee role or employment status is required.

The owner department remains responsible for completing or terminating the request.
## Step 13 Customer Support implementation

Customer Support is the first real department implementation. It may answer company-specific
questions only from tenant-scoped, requester-authorized knowledge evidence, provide reversible
troubleshooting, prepare an IT diagnostic collaboration, or prepare a human escalation. It cannot
execute refunds, payments, account or order changes, IT actions, approvals, or other mutations.
Human Resources, IT, Finance, and Procurement remain deterministic placeholders.

## Step 14 IT implementation

IT is now real alongside Customer Support. It answers authorized IT questions, prepares access and
identity operations, performs tenant-scoped inventory/software checks, diagnoses incidents, accepts
Customer Support diagnostics, and prepares Finance, Procurement, or technician handoffs. IT does not
spend money, approve budgets, choose suppliers, execute identity-provider operations, transfer
assets, or claim physical work is complete. HR, Finance, and Procurement remain placeholders.

## Step 15 Finance implementation

Finance is now real alongside Customer Support and IT. It answers authorized Finance questions,
reads tenant-scoped budgets, performs deterministic availability checks, creates controlled
reservations, accepts IT and future Procurement financial-validation collaboration, prepares human
spending approval, and records authorized confirmed financial movements. Finance cannot choose
suppliers, source products, execute purchases or payments, initiate bank transfers, or approve
restricted spending. Human Resources and Procurement remain placeholders.
