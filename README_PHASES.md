# Custom Accounting Add‑on – Phase‑wise Implementation Plan
*Derived from “Custom Accounting Full Implementation Plan” (Section 12) – Odoo 18*

---

## Overview
| Phase | Duration (weeks) | Focus | Gate before start |
|------|-------------------|-------|-------------------|
| **Phase 0** | 2 | Baseline & safety‑gate validation | – |
| **Phase 1** | 3 | Core accounting hardening | Phase 0 sign‑off |
| **Phase 2** | 4 | Product, inventory & customizable‑desk integration | Desk model decision (Sec 16‑1) |
| **Phase 3** | 3 | Operational workflows (sales, purchase, banking, OCR) | Phase 2 complete |
| **Phase 4** | 3 | Reporting & statutory outputs (GSTR‑1/3B, financials) | Phase 3 complete |
| **Phase 5** | 2 | Security, UX polish & release packaging | Phase 4 complete |
| **Total** | **≈ 17 weeks** | First production release | All gates approved |

> **Buffer** – add 1‑2 weeks per phase if Phase 0 uncovers material differences.

---

## Phase 0 – Baseline & Safety Gate (2 wks)

| Task | Owner | Acceptance |
|------|-------|------------|
| Freeze current addon set & DB backup procedure | DevOps | Documented list, backup script tested |
| Confirm Odoo version, Python env, PostgreSQL, enabled companies | DevOps | Signed‑off matrix |
| Run existing custom‑module test suite; log failures (no code changes) | QA | Test‑run report |
| **Validate Section 2 assumptions** (addon existence, `account.move._post` override, Community vs Enterprise, `l10n_in` GST) | Lead Dev + BA | Signed‑off *Current‑State Memo* |
| Produce Community‑vs‑Enterprise compatibility matrix per addon | Lead Dev | Matrix spreadsheet |
| **Decision workshop** – approve desk model (variant / kit / BOM / configurator) & tax‑jurisdiction scope (Sec 16) | PO / Stakeholders | Decision record |

**Deliverable:** *Current‑State Memo* + *Compatibility Matrix* + *Decision Log* (all version‑controlled).

---

## Phase 1 – Core Accounting Hardening (3 wks)

| Backlog Item (User Story) | Reference | Done‑Definition |
|---------------------------|-----------|-----------------|
| Central shared validation helpers (company, period, partner, tax, account, duplicate, analytic) | Sec 12‑P1 | Unit tests ≥ 90 % coverage |
| Audit `account.move._post` override for safe cooperation | Sec 2.2‑2 | Integration test matrix (invoice, bill, payment, recurring, asset, deferral, expense, GST) |
| Enforce balanced‑entry invariant on every custom entry path | Sec 9‑Invariants | Automated test: every posted move debit = credit |
| Idempotency protection for cron‑generated depreciation, deferral, recurring moves | Sec 12‑P1 | Re‑run cron → no duplicate lines |
| Structured audit metadata on every move (source model, source record, actor, timestamp, reversal link) | Sec 12‑P1 | Metadata visible in `account.move` form view |
| Period‑lock enforcement (Odoo lock dates + custom policy) | Sec 2.3‑69 | Attempt to post in locked period → ValidationError |

**Deliverable:** Hardened `custom_accounting_core` module + test suite + updated *Current‑State Memo* (if any).

---

## Phase 2 – Product, Inventory & Customizable‑Desk (4 wks)

> **Pre‑condition:** Desk product model decision signed off (Sec 16‑1).

| Backlog Item | Reference | Done‑Definition |
|--------------|-----------|-----------------|
| Implement chosen desk model (variant / kit / BOM / configurator) | Sec 12‑P2, Sec 4 | Product UI matches wireframe 6.3 |
| Configure product‑category valuation, income/expense, stock input‑output accounts | Sec 7 | Chart‑of‑Accounts verification script passes |
| End‑to‑end sales flow: inquiry → quotation → order → delivery → invoice → payment (incl. returns, credit/debit memos) | Sec 5.1, Fig 3 | Scenario T01‑T07 pass |
| End‑to‑end purchase flow: request → RFQ → PO → receipt (backorder) → vendor bill → payment | Sec 5.2, Fig 4 | Scenario T10‑T15 pass |
| GST tax behaviour validation (CGST+SGST intra‑state, IGST inter‑state) on desk lines | Sec 9, Sec 11 | Tax‑matrix test cases (incl. ₹10 000 + ₹1 800 example) |
| Inventory valuation & COGS posting on delivery / receipt | Sec 5.1‑5.2 | GL entries match worked examples (Sec 5.3) |

**Deliverable:** `custom_accounting_desk` module (or extensions) + integration test pack.

---

## Phase 3 – Operational Workflows (3 wks)

| Backlog Item | Reference | Done‑Definition |
|--------------|-----------|-----------------|
| Invoice / bill / payment posting & reconciliation links (auto‑match, manual match) | Sec 12‑P3 | Reconciliation UI (wireframe 6.4) functional |
| CSV/XLSX bank import – preview, row‑level errors, duplicate detection, atomic rollback | Sec 12‑P3 | Import of sample file → 0 unmatched, rollback on error |
| OCR vendor‑bill review – file‑type limits, dup detection, manual override, **no auto‑post without approval** | Sec 12‑P3, Wireframe 6.4 | OCR flow test (PDF → review → create bill) |
| Asset creation from bill lines; disposal / transfer / revaluation flows | Sec 12‑P3 | Asset register matches posted move lines |
| Analytic distribution mandatory policy enforcement | Sec 2.3‑70, Sec 7‑174 | Validation error when missing analytic on required moves |

**Deliverable:** `custom_accounting_operations` module + updated test scenarios (Sec 17).

---

## Phase 4 – Reporting & Statutory Outputs (3 wks)

| Backlog Item | Reference | Done‑Definition |
|--------------|-----------|-----------------|
| Trial Balance, General Ledger, P&L, Balance Sheet, Cash Flow, Aging – all reconciled to posted `account.move.line` | Sec 10, Sec 12‑P4 | Report totals = Σmove lines (automated check) |
| Configurable report filters: company, journal, account, partner, analytic, date range | Sec 12‑P4 | UI matches wireframe 6.5 |
| GSTR‑1 / GSTR‑3B aggregation from posted GST invoices & credit‑debit notes | Sec 12‑P4, Sec 11 | Export matches GST portal schema (sample file) |
| Mark e‑invoice / e‑way‑bill / GST‑portal filing as **external integration boundaries** (credentials, separate test plan) | Sec 12‑P4 | Integration spec doc |

**Deliverable:** `custom_accounting_reports` module + GSTR export files + integration spec.

---

## Phase 5 – Security, UX & Release (2 wks)

| Backlog Item | Reference | Done‑Definition |
|--------------|-----------|-----------------|
| Role‑based access test matrix (Accounting User, Manager, Finance Controller, Auditor, CFO/Admin) – Auditor read‑only everywhere | Sec 13‑RACI, Sec 12‑P5 | Automated ACL test suite passes |
| Bank‑detail masking for unauthorized roles | Sec 12‑P5 | UI inspection + unit test |
| UI polish – menus, breadcrumbs, status bars, error messages consistent with wireframes (Sec 6) | Sec 12‑P5 | UX checklist signed off |
| Packaging: upgrade scripts, demo data, migration notes, rollback plan, release checklist | Sec 12‑P5 | `release/` folder with all artefacts |
| **Release Gate** – all traceability scenarios (Sec 17) pass, invariants hold under regression suite | Sec 17‑3 | Signed release sign‑off |

**Deliverable:** Production‑ready Odoo addon package (`custom_accounting` top‑level app) + release notes.

---

## Cross‑Phase Artefacts (kept up‑to‑date)

| Artefact | Owner | Updated In |
|----------|-------|------------|
| Current‑State Memo (Sec 2) | Lead Dev | Phase 0 |
| Compatibility Matrix (Community/Enterprise) | Lead Dev | Phase 0 |
| Decision Log (desk model, jurisdictions, menu placement, OCR/e‑invoice scope, approval limits) | PO | Phase 0‑1 |
| Test Traceability Matrix (Sec 18) | QA | Every phase |
| Budget Tracker (person‑weeks vs actual) | PM | Every phase |
| Risk Register (Sec 15) | PM | Review each sprint |

---

## How to Use This README
1. **Check gates** – before starting a phase verify the “Gate before start” column is satisfied.  
2. **Pick backlog items** – each row maps to a Jira/GitHub issue; assign owner & estimate.  
3. **Run phase‑level Definition of Done** – all Done‑Definitions must be green before moving on.  
4. **Update artefacts** – keep the cross‑phase artefacts current; they feed the next phase’s planning.  

---

*Generated from the full implementation plan (Section 12) – keep this file in the repo root (`README_PHASES.md`) and version‑control alongside the addon source.*