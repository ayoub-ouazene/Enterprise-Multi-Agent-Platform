# 9. RAG and Company Knowledge

## 9.1 One Index and One Namespace Per Company

Version 1 uses one configured Pinecone index. Each company receives one
deterministic namespace derived by the backend from its trusted company ID:

```text
<configured-prefix>_<company-uuid>
```

The namespace is the primary vector tenant boundary. `company_id` remains in
record metadata as defense in depth. Clients cannot choose a namespace or
supply a trusted company ID.

Do not create a separate physical collection for every department unless later required.
Departments share their company's namespace and are separated by metadata filters.

## 9.2 Metadata

Each document chunk should contain metadata such as:

- company ID;
- department scope;
- document type;
- access scope;
- source file;
- version;
- upload timestamp;
- effective date when available.

## 9.3 Department Filtering

The HR agent retrieves HR and shared documents.

The IT agent retrieves IT and shared documents.

Finance and Procurement may retrieve shared purchasing policies.

Customer Support retrieves customer-facing and product knowledge according to access permissions.

## 9.4 Source Types

- policies;
- procedures;
- manuals;
- product documentation;
- troubleshooting guides;
- benefits documents;
- finance rules;
- procurement criteria;
- internal instructions.

## 9.5 Ingestion Pipeline

```text
Upload
→ file validation
→ text extraction
→ cleaning
→ chunking
→ metadata assignment
→ embedding
→ Pinecone upsert
```

## 9.6 Retrieval Behavior

Retrieval must use only the authenticated company's namespace and must also
filter by company ID metadata.

Additional filters may include:

- department;
- document type;
- access scope;
- active version.

Access scope is derived by the backend from the authenticated actor. Namespace,
company ID, and allowed access scopes are never accepted from normal client input.

## 9.7 Business Rules

Most company rules should be retrieved.

Executable tools are used only when calculation, database validation, or system action is required.

## 9.8 Updates and Versions

When a company uploads a new policy version:

- mark the old version inactive when appropriate;
- preserve metadata for audit;
- retrieve only the active version by default.

## 9.9 User-Facing Answers

When appropriate, answers should mention the policy source in a user-friendly way.

Internal vector IDs, embedding details, and raw retrieved chunks must not be exposed.
