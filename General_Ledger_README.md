# Accounting Feature Guide & Architecture Mapping

This guide explains where all the core accounting features you requested are located within your Odoo 18 project (`D:\Odoo18`), including how they work under the hood and where you can find them in the Odoo User Interface (UI).

---

## 1. Core Accounting Engine

### Double-entry accounting, Journal entries and journal lines
* **UI Navigation:** `Accounting > Accounting > Journal Entries` (or `Accounting > Journal Items`).
* **Where to find it:** Standard Odoo's `account.move` (Journal Entries/Headers) and `account.move.line` (Journal Items) models.
* **Architecture:** Odoo's native accounting engine operates strictly on double-entry principles. Every transaction (Invoice, Bill, Payment) creates an `account.move` record with multiple `account.move.line` records.
* **Source Path:** `odoo/addons/account/models/account_move.py`

### Debit and credit validation & Balanced posting enforcement
* **UI Navigation:** Happens automatically in the background when you click **"Post"** on any entry.
* **Where to find it:** Enforced at the core by `account.move` and hardened by `custom_accounting_core`.
* **Architecture:** Odoo inherently blocks posting if `sum(debits) != sum(credits)`. In Phase 1 of our plan, we are adding extra explicit balanced-entry tests at every custom entry-creation path within `custom_accounting_core` to prevent even draft imbalances.

### Reversals instead of deleting posted entries
* **UI Navigation:** Open any posted Journal Entry, Customer Invoice, or Vendor Bill and click the **"Reverse Entry"** or **"Add Credit Note"** button.
* **Where to find it:** Standard Odoo feature (Reversal/Credit Notes).
* **Architecture:** Once an `account.move` is posted, it cannot be deleted. You must reverse it. The reversal keeps a link to the original move (`reversed_entry_id`). This ensures compliance.
* **Source Path:** `odoo/addons/account/wizard/account_move_reversal.py`

---

## 2. Ledgers & Reporting

### General ledger & Trial balance
* **UI Navigation:** `Accounting > Reporting > General Ledger` and `Accounting > Reporting > Trial Balance`.
* **Where to find it:** The underlying data is just grouped `account.move.line` records. The visual reports are located in `custom_accounting_reports`.
* **Architecture:** Instead of a separate sub-engine, the Trial Balance and General Ledger simply query posted `account.move.line` records, grouping them by `account.account`.

### Customer and supplier subledgers
* **UI Navigation:** `Accounting > Reporting > Partner Ledger` (or Aged Receivable / Aged Payable reports).
* **Where to find it:** Standard Odoo `res.partner` combined with `account.move.line`.
* **Architecture:** There are no separate tables for subledgers. A customer subledger is simply the General Ledger filtered where the `partner_id` equals the customer and the account type is `asset_receivable`. Supplier subledgers filter by `liability_payable`.

---

## 3. Configuration & Master Data

### Account hierarchy and chart of accounts
* **UI Navigation:** `Accounting > Configuration > Chart of Accounts`.
* **Where to find it:** Standard Odoo `account.account` and `account.group` models.
* **Architecture:** Configured per company.
* **Source Path:** `odoo/addons/account/models/account_account.py`

### Company-wise accounting configuration
* **UI Navigation:** Toggle companies in the **top-right navigation bar** of the UI, or configure them via `Settings > Users & Companies > Companies`.
* **Where to find it:** Odoo's multi-company environment (`res.company`).
* **Architecture:** Almost all accounting records (`account.move`, `account.account`, `account.journal`) have a `company_id` field. Configuration is strictly segmented per company.

### Configurable accounts, taxes, journals, and analytic rules
* **UI Navigation:** 
  - Taxes: `Accounting > Configuration > Taxes`
  - Journals: `Accounting > Configuration > Journals`
  - Analytic Accounts: `Accounting > Configuration > Analytic Accounts`
* **Where to find it:** 
  - Taxes: `account.tax` (Standard) and `l10n_in*` (for GST).
  - Journals: `account.journal` (Standard).
  - Analytic Rules: `custom_accounting_analytic` module.
* **Architecture:** Found under the Configuration menus. The `custom_accounting_analytic` module enforces whether certain transactions *must* have an analytic distribution (cost center) attached before posting.

---

## 4. Operational & Compliance Features

### Fiscal periods and lock dates
* **UI Navigation:** `Accounting > Configuration > Settings` under the **"Fiscal Periods"** or **"Lock Dates"** section.
* **Where to find it:** Odoo's native lock dates feature, extended by your `custom_accounting_core`.
* **Architecture:** Odoo uses "Lock Dates" to prevent modifications prior to a certain date. Your custom implementation plan dictates adding custom period policies on top of this.

### Opening balances
* **UI Navigation:** `Accounting > Configuration > Settings > Review Opening Balances` (or directly via a Journal Entry dated on your fiscal year start).
* **Where to find it:** Managed within `custom_accounting_core` and standard Odoo.
* **Architecture:** Opening balances are just a special `account.move` posted to a suspense or equity account on day 1 of the fiscal year.

### Recurring journal entries
* **UI Navigation:** `Accounting > Accounting > Recurring Transfers` (or via custom scheduled actions in your module).
* **Where to find it:** `custom_accounting_core` (or `account_recurring` if using Enterprise).
* **Architecture:** Uses scheduled actions (cron jobs) to duplicate a template `account.move` automatically at set intervals.

### Audit trail and source-document tracking
* **UI Navigation:** Scroll to the bottom of any Invoice, Bill, or Journal Entry to view the **Chatter** (the messaging thread and log). Source documents are visible in fields like "Source Document" on invoices.
* **Where to find it:** Handled by the "Chatter" (Odoo's `mail.thread` mixin) and standard relational fields (e.g., `invoice_origin`).
* **Architecture:** Every posted move is immutable. Tracking who did what is recorded in the message chatter. Phase 1 adds structured audit metadata (source model, actor, timestamp) centrally.

### Duplicate transaction prevention
* **UI Navigation:** If you try to save a Vendor Bill with a reference you already used for that Vendor, a warning popup will appear in the UI.
* **Where to find it:** Validation layer in `custom_accounting_core` & `custom_accounting_ocr`.
* **Architecture:** Before a vendor bill or manual journal can be saved or posted, the system checks for uniqueness (e.g., matching Vendor + Vendor Reference). 

---

## How to navigate this in your codebase

To visually inspect these features, you can search your `D:\Odoo18` folder for the following models:
- Search for `_name = "account.move"` or `_inherit = "account.move"` to see Journal Entry logic.
- Search for `_name = "account.account"` to see Chart of Account logic.
- Look inside `D:\Odoo18\addons\custom_accounting_*` modules for the custom validation overrides and custom reports.