# 13. Company Onboarding and Data Import

## 13.1 Version 1 Input

Companies upload spreadsheets and documents.

Typical spreadsheets:

- employees;
- managers;
- departments;
- assets;
- budgets;
- suppliers;
- leave balances;
- software catalog.

## 13.2 Import Process

```text
Company signup
→ upload sheets
→ detect entity type
→ detect columns
→ map standard fields
→ map extra fields to custom_data
→ show preview
→ company submits corrections
→ confirm mapping
→ validate
→ import
```

## 13.3 Intelligent Mapping

The LLM may propose mappings such as:

```text
Worker Number → employee_code
Full Name → name
Work Mail → email
Unit → department
Office Floor → custom_data.office_floor
```

## 13.4 Confirmation

Confirmation is required as part of company onboarding.

The company can provide corrections through a natural-language input.

The system shows the final mapping before import.

## 13.5 Validation

The import process should detect:

- missing required fields;
- duplicate records;
- invalid emails;
- unknown departments;
- invalid manager references;
- malformed numbers and dates;
- unrecognized columns.

## 13.6 Custom Fields

Core fields use relational columns.

Additional company-specific fields go to JSONB `custom_data`.

The platform may later store field-definition metadata for dynamic forms and validation.

## 13.7 Post-Onboarding Editing

Authorized department managers and the Company account can view permitted data.

They can request edits through natural language.

The backend:

1. parses the requested edit;
2. creates a structured proposed change;
3. checks authorization;
4. shows a preview;
5. applies the change after confirmation;
6. records an audit event when needed.

## 13.8 Future Integrations

Postponed:

- direct database views;
- APIs;
- ERP connectors;
- hybrid uploaded and connected data.

These should use adapters that map company-specific schemas to the platform's standard service functions.
