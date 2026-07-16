# 14. Authentication, Permissions, and Multi-Tenancy

## 14.1 Authentication

All protected actions require authentication.

The authenticated context contains:

- user ID;
- company ID;
- actor type;
- employee ID when applicable;
- department;
- manager status;
- permission claims.

## 14.2 Actor Permissions

### External User

- access only their company-specific Customer Support experience;
- access only their own requests.

### Employee

- create permitted requests;
- view their own requests;
- view permitted personal information;
- provide requested input.

### Department Manager

- employee capabilities;
- department request monitoring;
- department approvals;
- human actions;
- department data management.

### Company Account

- company-wide configuration;
- company data;
- policy and document management;
- employee and manager management;
- failures and capability gaps.

## 14.3 Data Visibility

Each actor sees only normally authorized information.

Examples:

- employees do not see confidential budget values;
- IT managers do not automatically edit HR or Finance data;
- external users do not see internal department communication;
- Company accounts can see broader company information.

## 14.4 Tenant Isolation

Every tenant-owned query is scoped by company ID.

The company ID is derived from authentication.

It must not be trusted from normal request bodies.

## 14.5 Repository Scoping

Repositories are created with the company context.

All tenant-owned operations automatically include that company filter.

## 14.6 RAG Isolation

Every Pinecone retrieval includes company metadata filtering.

Department and access filters are additionally applied.

## 14.7 Natural-Language Editing Permissions

- IT manager: permitted IT data.
- HR manager: permitted HR data.
- Finance manager: permitted Finance data.
- Procurement manager: permitted Procurement data.
- Company account: broader permitted company data.

## 14.8 Audit

Important mutations, approvals, rejections, financial confirmations, and natural-language data edits should produce audit-relevant records.
