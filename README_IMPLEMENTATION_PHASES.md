# Custom Accounting Add-on for Odoo 18

## Phased Implementation README

**Source plan:** `D:\Odoo18\Custom_Accounting_Full_Implementation_Plan.docx`  
**Purpose:** convert the full implementation plan into an execution sequence that can be reviewed and approved phase by phase before development starts.

This README is a delivery checklist, not source code. Every phase has an objective, work packages, dependencies, deliverables, tests, and an exit gate. A later phase must not be treated as complete merely because its code exists; its tests and business acceptance must also pass.

## 1. Overall delivery sequence

```text
Phase 0: Baseline and safety gate
                |
                v
Phase 1: Core accounting hardening
                |
                v
Phase 2: Product, inventory, sales and purchase integration
                |
                v
Phase 3: Operational workflows and transaction processing
                |
                v
Phase 4: Reporting, GST and statutory outputs
                |
                v
Phase 5: Security, UX, migration and production release
```

Indicative duration from the source plan: **17 weeks**.

| Phase | Duration | Main result | Depends on |
|---|---:|---|---|
| 0 | 2 weeks | Verified Odoo baseline and approved technical starting point | None |
| 1 | 3 weeks | Safe, reusable accounting validation and posting controls | Phase 0 gate |
| 2 | 4 weeks | Product, inventory, sales and purchase flows connected to accounting | Phase 1 gate and desk-model decision |
| 3 | 3 weeks | Payments, reconciliation, bank import, OCR and operational controls | Phase 2 core flows |
| 4 | 3 weeks | Financial, GST, Cash Book, Petty Cash and statutory-preparation reports | Posted data from Phases 1–3 |
| 5 | 2 weeks | Permissions, usability, migration package and release approval | All previous phase gates |

## 2. Rules that apply to every phase

- Odoo's `account.move` and `account.move.line` remain the single posting authority.
- Do not build a second ledger or write balances directly.
- Every posted move must be balanced: total debit equals total credit.
- Use configuration for accounts, taxes, journals, analytic rules, product categories and approval limits.
- Respect company access and Odoo accounting lock dates.
- Correct posted transactions by reversal, credit note or debit note; do not silently edit or delete them.
- External services such as OCR, e-invoice, e-way bill, banking and POS must fail gracefully and provide a manual fallback.
- Each phase must leave an audit trail containing the source document, actor, timestamp, posting result and reversal link where applicable.

## 3. Phase 0 — Baseline and safety gate

**Duration:** 2 weeks  
**Goal:** establish the real technical and business baseline before modifying anything.

### Work packages

- Inventory the actual addons under `D:\Odoo18\addons` and all custom accounting addons.
- Confirm the Odoo version, edition, Python environment, PostgreSQL connection, configured companies and database backup procedure.
- Confirm which features already come from standard Odoo, `l10n_in*`, Enterprise modules or custom modules.
- Inspect whether `custom_accounting_analytic` overrides `account.move._post`; identify every posting flow affected by that hook.
- Confirm whether GST calculation, GST fields, invoice printing, e-invoicing and e-way-bill functionality already exist in Indian localization modules.
- Run the existing custom-module test suite and record failures without changing unrelated code.
- Confirm current chart of accounts, journals, taxes, products, partners, access groups and lock-date policy.
- Record the current state in a signed baseline memo.

### Required outputs

- Addon inventory and dependency matrix.
- Community-versus-Enterprise compatibility matrix.
- Database backup and restore verification.
- Current posting-hook impact report.
- Confirmed GST/localization capability report.
- Baseline test report.
- Approved Phase-0 baseline memo.

### Exit gate

- [ ] The real `D:\Odoo18` installation has been inspected.
- [ ] The addon list and dependencies are confirmed.
- [ ] The Odoo edition is confirmed.
- [ ] The database can be backed up and restored.
- [ ] Existing test failures are recorded.
- [ ] The `account.move._post` impact is understood.
- [ ] The desk product model decision is scheduled or resolved.
- [ ] Finance and technical owners approve Phase 1 to begin.

## 4. Phase 1 — Core accounting hardening

**Duration:** 3 weeks  
**Goal:** create the safe accounting foundation that every later workflow uses.

### Work packages

- Centralize validation for company, date, period, partner, account, tax, duplicate documents and analytic distribution.
- Enforce active, non-deprecated accounts and valid company/journal relationships.
- Enforce balanced journal entries and atomic rollback when validation fails.
- Respect accounting lock dates and custom period controls.
- Add idempotency protection for recurring entries, depreciation, deferred recognition and other scheduled postings.
- Add structured audit metadata: source model, source record, actor, timestamp, action and reversal link.
- Preserve standard Odoo posting, reconciliation and reversal behavior.
- Define the canonical journal-rule catalog for sales, purchases, receipts, payments, assets, deferrals and inventory valuation.
- Establish the minimum chart-of-accounts and tax-account configuration required by later phases.

### Core data covered

`res.company`, `res.partner`, `account.account`, `account.journal`, `account.move`, `account.move.line`, `account.payment`, taxes, tax repartition, analytic plans and lock dates.

### Exit gate

- [ ] Every custom posting path uses the shared validation layer.
- [ ] Unbalanced and invalid entries are rejected without partial posting.
- [ ] Locked periods reject ordinary posting.
- [ ] Reversals preserve the original move and audit trail.
- [ ] Scheduled postings are idempotent.
- [ ] T04, T05 and the accounting invariants pass.
- [ ] Phase 1 regression results are approved.

## 5. Phase 2 — Product, inventory, sales and purchase integration

**Duration:** 4 weeks  
**Goal:** connect the operational sales and purchase journeys to inventory and accounting.

### 5.1 Product and customizable desk

- Decide whether the customizable desk is a product variant, kit, manufactured BOM or bespoke configurator.
- Configure product categories, income accounts, expense accounts, stock input/output accounts and valuation accounts.
- Model desk configuration attributes such as size, cable tray or other approved options.
- Test quotation, order, delivery, stock valuation, COGS, invoicing and returns for the selected model.

### 5.2 Sales flow from the reference images

Implement and test the complete business journey:

```text
Sales Support / Sales Activity
        -> Inquiry
        -> Quotation / RFQ
        -> Customer review and accept/reject loop
        -> Contract or Scheduling Agreement where applicable
        -> Sales Order
        -> Delivery or free-of-charge delivery
        -> Subsequent free-of-charge delivery where applicable
        -> Invoice / Debit Memo / Credit Memo
        -> Payment and receipt
        -> Reconciliation and accounting reports
```

The workflow must include the image-derived nodes: Sales Support, Sales Activity, Inquiry, Quotation, Contract, Scheduling Agreement, Sales Order, Returns, Delivery, Delivery free of charge, Subsequent delivery free of charge, Debit Memo, Invoice and Credit Memo.

### 5.3 Purchase flow from the reference image

Implement and test:

```text
Purchase Request
        -> Draft RFQ
        -> Review and validation
        -> Approved Purchase Order
        -> PO sent to vendor
        -> Product receipt
        -> Goods-available decision
        -> Pick products / Receipt Slip
        -> Partial receipt and backorder when required
        -> Vendor Bill
        -> Vendor-bill validation
        -> Purchase journal update
        -> Supplier payment and reconciliation
```

The automatic/manual distinction in the reference image must be captured in the design. Automatic transitions must be logged, and manual transitions must record the user and reason.

### 5.4 GST behavior

- Same-state transactions use CGST plus SGST.
- Inter-state transactions use IGST.
- Do not create a combined GST posting where the standard tax engine provides separate components.
- Test sales, purchases, returns, credit notes and debit notes across intra-state and inter-state cases.

### 5.5 Cash transaction requirement carried into implementation

The source DOCX at the path above is the earlier plan and does not contain the later Cash Transactions addition. The following requirement must be approved and added to the final backlog before Phase 2 is signed off:

- Sales and Purchase forms must provide a `Transaction Mode` dropdown with `Credit transaction` and `Cash transaction`.
- Cash sales post to an approved cash or petty-cash journal and do not leave an unintended receivable.
- Cash purchases post to an approved cash or petty-cash journal and do not leave an unintended payable.
- Store `transaction_mode`, cash journal, cash location, payment method and receipt/reference against the source transaction and resulting move.
- Add cash sale, cash purchase, cash-journal configuration and GST tests.

### Exit gate

- [ ] Desk product model is approved and configured.
- [ ] Sales and purchase flows create exactly one downstream document per transition.
- [ ] Returns, backorders, free-of-charge deliveries and memos are traceable.
- [ ] Inventory valuation and COGS reconcile to accounting.
- [ ] CGST/SGST and IGST behavior passes.
- [ ] Sales and purchase flows work for both credit and approved cash modes.
- [ ] T01, T03, T06, T07, T08, T09, IMG-S01–IMG-S10 and IMG-P01–IMG-P07 pass.

## 6. Phase 3 — Operational workflows and transaction processing

**Duration:** 3 weeks  
**Goal:** complete daily finance operations after documents have been created.

### Work packages

- Complete customer invoice, customer receipt, vendor bill and supplier payment flows.
- Reconcile receivables and payables with payments and source documents.
- Register payment through bank, main cash and petty-cash journals where permitted.
- Harden bank CSV/XLSX import with preview, row-level errors, duplicate detection and all-or-nothing commit.
- Complete bank reconciliation and unmatched-item handling.
- Harden OCR vendor-bill review with file limits, duplicate detection, confidence review, manual override and approval before posting.
- Validate asset creation from bill lines, depreciation, disposal, transfer and revaluation.
- Complete recurring entries, deferred revenue/expense recognition and follow-up/collection activities.
- Implement petty-cash operational records: custodian, voucher, purpose, expense account, tax, attachment, approval, top-up, transfer and bank deposit.
- Enforce petty-cash limits and approval rules.

### Exit gate

- [ ] Customer and supplier payments reconcile correctly.
- [ ] Bank import is previewable and duplicate-safe.
- [ ] OCR never auto-posts without the configured approval.
- [ ] Asset, depreciation and deferral entries are balanced and traceable.
- [ ] Petty-cash vouchers, top-ups and transfers reconcile to their journals.
- [ ] T02, T10, T11, T12 and relevant cash-operation tests pass.

## 7. Phase 4 — Reporting, GST and statutory outputs

**Duration:** 3 weeks  
**Goal:** make every operational and accounting result visible, reconcilable and exportable.

### Standard accounting reports

- Trial Balance.
- General Ledger.
- Profit and Loss.
- Balance Sheet.
- Cash Flow.
- Receivables and Payables Aging.
- Customer and supplier subledgers.
- Inventory valuation and COGS analysis.
- Asset and depreciation reports.
- Deferred revenue/expense schedules.
- Analytic profitability and budget-versus-actual reporting where those modules are approved.

### GST and statutory preparation

- Aggregate CGST, SGST and IGST from posted tax lines.
- Validate GSTR-1 and GSTR-3B preparation totals.
- Include sales invoices, purchase bills, returns, credit notes and debit notes.
- Keep e-invoice, e-way bill and GST portal submission behind explicit external-integration boundaries.
- Add credential, outage, retry, logging and manual-fallback tests for each external service.

### Cash Book and Petty Cash reports

These are required Accounts-module outputs, not optional dashboard widgets.

**Cash Book** must provide:

- Date range, company, cash journal, cash location, transaction mode, partner, account and reconciliation filters.
- Opening balance.
- Receipts, payments and transfers.
- Running balance and closing balance.
- Source document, receipt reference, user and reconciliation status.
- Print PDF and CSV/XLSX export.
- Drill-down to the posted journal entry.

**Petty Cash** must provide:

- Custodian and petty-cash journal filters.
- Opening float, top-ups, vouchers, approved amounts and reimbursements.
- Physical cash count, book balance, variance and authorized adjustment.
- Voucher attachments, approval state and source entry.
- Closing balance and audit history.

### Exit gate

- [ ] Every report reconciles to posted move lines.
- [ ] Cash Book reconciles to cash journals.
- [ ] Petty Cash reconciles to approved vouchers and physical counts.
- [ ] GST reports reconcile to tax-tagged move lines.
- [ ] Filters, exports, drill-downs and access rules work.
- [ ] T06, T07, T10 and all Cash Book/Petty Cash tests pass.

## 8. Phase 5 — Security, UX, migration and production release

**Duration:** 2 weeks  
**Goal:** make the completed implementation safe and usable in production.

### Work packages

- Test Accounting User, Accounting Manager, Finance Controller, Auditor and CFO/Admin roles separately.
- Ensure Auditor is read-only, including custom wizards and reports.
- Restrict bank details, cash controls, posting, payment, reversal and configuration actions by role.
- Standardize menus, breadcrumbs, status bars, labels and actionable error messages.
- Place Cash Book under Accounts reporting and Petty Cash under Accounts cash management, subject to the approved menu design.
- Prepare upgrade scripts, demo data, migration notes, rollback procedure and release checklist.
- Perform one parallel close or controlled pilot before decommissioning any manual process.
- Confirm backups, monitoring, scheduled jobs, credentials, external endpoints and support ownership.

### Final release gate

- [ ] All phase gates are approved.
- [ ] Security and record-rule tests pass for every role.
- [ ] Migration and rollback are rehearsed.
- [ ] Reports and GST totals are reconciled by Finance.
- [ ] User Acceptance Testing is signed off by Sales, Inventory and Accounting representatives.
- [ ] Production backup is verified.
- [ ] The release owner approves deployment.

## 9. Cross-phase feature coverage

| Requirement from the implementation plan | Phase(s) |
|---|---|
| Existing Odoo/addon/dependency inspection | 0 |
| Shared accounting validation and posting authority | 1 |
| Double-entry debit/credit controls | 1, all later phases |
| Chart of accounts, journals and tax configuration | 1–2 |
| Sales Support, inquiry, quotation, contract and scheduling agreement | 2 |
| Sales order, delivery, free-of-charge delivery and returns | 2 |
| Invoice, debit memo, credit memo and customer payment | 2–3 |
| Purchase request, RFQ, PO, receipt and backorder | 2 |
| Vendor bill, validation, supplier payment and reconciliation | 2–3 |
| Product, inventory valuation and COGS | 2 |
| Customizable desk | 0 decision, 2 implementation |
| GST CGST/SGST/IGST | 1–2, reported in 4 |
| Banking import and reconciliation | 3 |
| OCR capture and review | 3 |
| Assets and depreciation | 1 foundation, 3 operations |
| Deferred recognition and recurring entries | 1 foundation, 3 operations |
| Follow-up and collections | 3 |
| Trial Balance, GL, P&L, Balance Sheet and Cash Flow | 4 |
| Aging, analytic and budget reporting | 4 |
| GSTR-1 and GSTR-3B preparation | 4 |
| E-invoice/e-way bill boundary | 4, separate credentials and tests |
| Security, roles and bank-field protection | 5 |
| Cash transaction mode in Sales and Purchase | 2, follow-up requirement |
| Cash Book | 4, follow-up requirement |
| Petty Cash | 3–4, follow-up requirement |

### Addon and component coverage

| Component from the source plan | Responsibility | Phase |
|---|---|---|
| `custom_accounting_core` | Recurring entries, opening balances, expenses and shared accounting foundations | 0–1 |
| `custom_accounting_analytic` | Analytic plans, mandatory distribution and profitability | 1, 4 |
| `custom_accounting_assets` | Categories, schedules, depreciation, disposal, transfer and revaluation | 1, 3–4 |
| `custom_accounting_budget` | Budgets, actuals, variance and revisions | 1 configuration, 4 reporting |
| `custom_accounting_dashboard` | Receivable, payable, cash, GST and approved budget KPIs | 4–5 |
| `custom_accounting_deferred` | Revenue and expense recognition schedules | 1, 3–4 |
| `custom_accounting_followup` | Overdue levels, reminders and activities | 3 |
| `custom_accounting_indian` | GSTR-1 and GSTR-3B preparation | 4 |
| `custom_accounting_ocr` | Vendor-bill upload, review and provider boundary | 3 |
| `custom_accounting_reports` | Financial statements, aging, analysis and exports | 4 |
| `custom_accounting_security` | Roles, model access and bank-field protection | 5 |
| `custom_bank_reconciliation` | Bank statement import and unmatched-item queue | 3 |
| `l10n_in*` and `l10n_in_gst_invoice_customization` | Indian taxes, GST fields, invoice output and any existing e-invoice/e-way-bill capability | 0 validation, 2 configuration, 4 boundary tests |

### Authoritative data-model coverage

The implementation must extend these Odoo records rather than create a competing accounting database:

- `res.company`: company, currency, fiscal and lock-date context.
- `res.partner`: customer, supplier, receivable/payable and GST identity.
- `sale.order` and order lines: inquiry/quotation/order and sales source data.
- `purchase.order` and order lines: request/RFQ/PO source data.
- `account.move`: invoice, bill, debit memo, credit memo and journal header.
- `account.move.line`: posted debit/credit, tax, analytic and partner subledger lines.
- `account.account`: chart of accounts and account types.
- `account.journal`: sales, purchase, bank, main-cash and petty-cash journals.
- `account.payment` and reconciliations: customer receipts and supplier payments.
- `product.product`, `product.template`, `stock.move` and valuation layers: product, inventory, delivery, receipt, COGS and valuation.
- Tax and tax-repartition records: CGST, SGST and IGST calculation and reporting tags.
- Asset, deferred, analytic, budget, OCR, bank-import and follow-up records where the corresponding optional component is approved.

## 10. Testing sequence

### Phase-level testing

- **Phase 0:** environment, backup/restore, module loading, existing test inventory and baseline failures.
- **Phase 1:** validation, balanced posting, lock dates, duplicate policy, idempotency, reversal and audit trail.
- **Phase 2:** sales, purchase, inventory, GST, desk configuration, returns, backorders, free-of-charge flows and cash-mode posting.
- **Phase 3:** receipts, payments, bank import, reconciliation, OCR, assets, deferrals, recurring entries and petty cash operations.
- **Phase 4:** report-to-ledger reconciliation, GST aggregation, Cash Book, Petty Cash, filters, export and drill-down.
- **Phase 5:** role security, usability, migration, rollback, backup and release regression.

### Mandatory source-plan scenarios

- T01: credit sale with CGST and SGST.
- T02: customer receipt and zero customer balance after reconciliation.
- T03: credit purchase with input CGST and SGST.
- T04: unbalanced manual journal rejected.
- T05: missing date/account/tax/period rejected.
- T06: same-state sale produces CGST and SGST.
- T07: inter-state sale produces IGST.
- T08: customizable-desk sale links stock, COGS, invoice, tax and payment.
- T09: customizable-desk return is traceable.
- T10: month close produces a balanced adjusted trial balance and lock behavior.
- T11: year close applies retained-earnings and opening-balance policy.
- T12: posted reversal preserves the original transaction.
- IMG-S01–IMG-S10: sales accept/reject, automation, delivery, return, memos and payment scenarios.
- IMG-P01–IMG-P07: purchase validation, PO, partial receipt, backorder, vendor bill, payment and automation scenarios.

### Additional Cash Transactions scenarios to add

- CT01: cash sale posts to cash and GST accounts with no unintended receivable.
- CT02: cash purchase posts to cash and input-tax accounts with no unintended payable.
- CT03: cash mode without a valid cash journal, location or receipt reference is rejected.
- CT04: petty-cash voucher above the approval limit is rejected.
- CT05: approved petty-cash voucher posts to the expense and petty-cash accounts.
- CT06: petty-cash top-up, transfer and bank deposit remain balanced and traceable.
- CT07: Cash Book opening balance plus receipts minus payments plus/minus transfers equals the posted closing balance.
- CT08: Petty Cash physical count, book balance, variance explanation and adjustment remain auditable.

## 11. Decisions required before implementation starts

- [ ] Community or Enterprise edition confirmed.
- [ ] Actual installed addons and overrides confirmed.
- [ ] Customizable desk model selected.
- [ ] India-only or multi-company/multi-jurisdiction scope selected.
- [ ] Custom suite menu placement approved.
- [ ] First-release features separated from later phases.
- [ ] OCR, bank, e-invoice and e-way-bill integration scope approved.
- [ ] Cash transaction mode approved for Sales and Purchase.
- [ ] Cash journals, petty-cash custodians and approval limits approved.
- [ ] Cash Book and Petty Cash report formats approved.
- [ ] Posting, payment, reversal, asset and configuration approval limits approved.

## 12. Implementation operating procedure

For each phase:

1. Review the phase scope and confirm dependencies.
2. Freeze the acceptance criteria before coding.
3. Create the phase branch and database backup.
4. Implement models, views, security, reports and tests together.
5. Run the phase test set and the full regression suite.
6. Demonstrate the business flow to the relevant users.
7. Record open defects, decisions and deviations.
8. Obtain the phase exit-gate approval.
9. Only then begin the next phase.

## 13. Source-plan notes

- The source DOCX contains the original six-phase schedule, team/RACI section, budget framework, risk register, open decisions, testing strategy and requirement traceability matrix.
- The schedule totals approximately 35 person-weeks: Phase 0 3.5, Phase 1 6, Phase 2 8.5, Phase 3 7, Phase 4 6 and Phase 5 4.
- The Cash Transactions, Cash Book and Petty Cash requirements were added to this README as a follow-up requirement because they are not present in the source DOCX at the supplied path. They must be merged into the approved master plan before development begins.
- No implementation should start until Phase 0 and the decisions in Section 11 are approved.
