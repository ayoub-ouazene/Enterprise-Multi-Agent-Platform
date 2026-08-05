# Example Onboarding Data

This folder contains **ready-to-use mock data** for testing the Orchestra signup and onboarding flow end-to-end. All data is fictional and safe to commit to a public repository.

> **Company used in all examples:** Northstar Labs (slug: `northstar-labs`)

---

## Quick Start

### 1. Sign up a new company

Open the Orchestra frontend at `http://localhost:5173/signup` and fill in:

| Field | Value |
|-------|-------|
| Company name | `Northstar Labs` |
| Company slug | `northstar-labs` |
| Email | `admin@northstar.example.com` |
| Password | `DemoPass#2026!` |
| Confirm password | `DemoPass#2026!` |

Or send the equivalent API request:

```bash
curl -X POST http://localhost:8000/api/v1/companies/register \
  -H "Content-Type: application/json" \
  -d @examples/onboarding-data/00_company_signup.json
```

### 2. Upload departments

In the onboarding wizard → **Departments** step, upload:

```
examples/onboarding-data/01_departments.csv
```

This enables all 5 departments (Customer Support, HR, IT, Finance, Procurement).

### 3. Upload employees

In the **Employees** step, upload:

```
examples/onboarding-data/02_employees.csv
```

This imports 15 employees across all 5 departments. Each employee has a temporary password `TempPass#2026!` that they must change on first login.

### 4. Assign managers

In the **Managers** step, upload:

```
examples/onboarding-data/03_manager_assignments.csv
```

This assigns the 5 department directors as managers and links their direct reports.

### 5. Upload policies

In the **Policies** step, upload each policy document from:

```
examples/onboarding-data/policies/
```

| File | Department scope | Title to enter |
|------|-----------------|----------------|
| `00_shared_code_of_conduct.md` | Shared | Northstar Labs Code of Conduct |
| `01_customer_support_policy.md` | Customer Support | Customer Support Policy |
| `02_hr_policy.md` | Human Resources | Human Resources Policy |
| `03_it_policy.md` | Information Technology | IT Policy |
| `04_finance_policy.md` | Finance | Finance Policy |
| `05_procurement_policy.md` | Procurement | Procurement Policy |

> **Tip:** Uploading the shared Code of Conduct alone satisfies the policy requirement for all departments. Upload the department-specific policies for richer RAG answers.

### 6. Activate the company

Once all onboarding checks are satisfied, click **Activate** in the **Review** step. The company workspace is now live.

---

## File Reference

```
examples/onboarding-data/
├── 00_company_signup.json          # Signup form values (JSON)
├── 01_departments.csv              # 5 departments
├── 02_employees.csv                # 15 employees with manager links
├── 03_manager_assignments.csv      # Manager hierarchy
├── README.md                       # This file
└── policies/
    ├── 00_shared_code_of_conduct.md
    ├── 01_customer_support_policy.md
    ├── 02_hr_policy.md
    ├── 03_it_policy.md
    ├── 04_finance_policy.md
    └── 05_procurement_policy.md
```

---

## CSV Column Reference

### `01_departments.csv`

| Column | Required | Description |
|--------|----------|-------------|
| `department_type` | Yes | One of: `customer_support`, `hr`, `it`, `finance`, `procurement` |
| `name` | Yes | Display name for the department |
| `is_active` | No | `true` or `false` (default: `true`) |
| `custom_data` | No | JSON string for extra fields |

### `02_employees.csv`

| Column | Required | Description |
|--------|----------|-------------|
| `email` | Yes | Unique employee email |
| `first_name` | Yes | First name |
| `last_name` | Yes | Last name |
| `temporary_password` | Yes | Initial password (min 12 chars, must include upper/lower/number) |
| `employee_code` | Yes | Unique employee code |
| `department` | Yes | Department name (must match a department from `01_departments.csv`) |
| `job_title` | Yes | Job title |
| `employment_status` | Yes | One of: `active`, `inactive`, `on_leave`, `terminated` |
| `manager_email` | No | Email of the employee's manager |
| `custom_data` | No | JSON string for extra fields |

### `03_manager_assignments.csv`

| Column | Required | Description |
|--------|----------|-------------|
| `employee_email` | Yes | Email of the employee |
| `manager_email` | Yes | Email of the manager (leave empty for top-level directors) |

---

## Demo Credentials Summary

After onboarding with this data, you can log in as:

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| Company admin | `admin@northstar.example.com` | `DemoPass#2026!` | Created during signup |
| IT Manager | `sarah.chen@northstar.example.com` | `TempPass#2026!` | Must change on first login |
| HR Manager | `emma.rodriguez@northstar.example.com` | `TempPass#2026!` | Must change on first login |
| Finance Manager | `james.thompson@northstar.example.com` | `TempPass#2026!` | Must change on first login |
| Procurement Manager | `ava.mitchell@northstar.example.com` | `TempPass#2026!` | Must change on first login |
| Support Manager | `isabella.clark@northstar.example.com` | `TempPass#2026!` | Must change on first login |
| Employee (IT) | `marcus.lee@northstar.example.com` | `TempPass#2026!` | Must change on first login |

> **Company slug for login:** `northstar-labs`

---

## Notes

- All emails use the `.example.com` domain, which is reserved for documentation and testing (RFC 2606).
- All passwords are mock and follow the platform's password policy (12+ chars, upper/lower/number).
- The data is internally consistent: manager emails in `02_employees.csv` reference other employees in the same file, and `03_manager_assignments.csv` matches the hierarchy.
- You can modify the data freely for your own testing scenarios.
