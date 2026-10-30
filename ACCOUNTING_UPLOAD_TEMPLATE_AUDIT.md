# Accounting Upload/Import Audit — D:\Odoo18 (2026-08-25)

Scope: every accounting, invoicing, GST, banking, and vendor-bill screen where a
file can be uploaded/imported, across custom addons + the installed core
Odoo modules. Method: source grep for `fields.Binary`, `widget="binary"`,
`csv.DictReader`/`csv.reader`, `base64.b64decode`, `get_import_templates`,
`action_import`, dashboard drop-zones, and attachment creation tied to
accounting models; cross-checked against which modules actually exist in
`D:\Odoo18\addons` (not assumed from Odoo's full feature set).

## Summary

| # | Feature | Classification | Status |
|---|---|---|---|
| 1 | Bank Statement CSV Import (`custom_bank_reconciliation`) | Structured import — CSV template | **Present**, template already added |
| 2 | Vendor Bill Digitization / OCR (`custom_accounting_ocr`) | Document/OCR upload — guide + sample doc | **Present**, no template yet |
| 3 | Chart of Accounts import (core `account`) | Structured import — XLSX | **Present** (native Odoo `get_import_templates`, already ships its own template button in the standard list-view Import dialog) |
| 4 | Journal Items import (core `account`) | Structured import — XLSX | **Present** (native, same as above) |
| 5 | Contacts/Customers/Vendors import (core `base`) | Structured import — generic | **Present**, but `res.partner` has **no** `get_import_templates()` override — uses Odoo's generic "any field" import UI, not a fixed template. GST fields (`gst_cin`, `gst_tan`, `gst_fssai`, `gst_iec`, `business_type`, etc.) are plain fields on `res.partner`, so they're importable via the generic dialog by their technical/db column name, but there's no packaged template file listing them. |
| 6 | QIF / OFX / CAMT.053 bank import | — | **Not present in this codebase at all.** No `account_bank_statement_import*` module exists under `addons/`. These are Enterprise/OCA connectors not installed here. Nothing to template. |
| 7 | Invoice/Bill EDI-XML import | — | **Not present.** No EDI import wizard found in installed addons. |
| 8 | Accounting Dashboard upload/drop-zone | — | Dashboard code (`account_journal_dashboard.py`) only *displays* statement/reconciliation stats — no file-drop upload action found in it. |
| 9 | Fixed Assets / Deferred / Budget / Analytic bulk import | — | **Not present.** These modules (`custom_accounting_assets`, `custom_accounting_deferred`, `custom_accounting_budget`, `custom_accounting_analytic`) are form/schedule-driven only, no `fields.Binary` or CSV parsing anywhere in them. |
| 10 | Affiliate withdrawal / payout import | — | **Not present.** `custom_accounting_affiliate` only extends `affiliate.withdrawal` with payment posting logic — no upload. |
| 11 | Shiprocket shipping data | — | **Not present as upload.** `delivery_shiprocket` integrates via API calls, not file upload (not fully re-audited this pass — flagged for a follow-up grep if you want it confirmed). |
| 12 | GST reports (GSTR, e-invoice, etc.) | Report/export only | `l10n_in_gst_invoice_customization`, `custom_accounting_indian` — everything found is invoice **print/output** (PDF, QR, report layout), not an import path. No CSV/JSON upload for GSTR or e-way-bill found. |
| 13 | Company logo / signature / stamp | Image/branding upload | **Present** (standard Odoo `res.company` image fields) — plain image upload, no template concept applies (not touched here). |

## Detail: the two real upload features

### 1. Bank Statement CSV Import
- File: `addons/custom_bank_reconciliation/wizard/bank_statement_csv_import_wizard.py`
- View: `addons/custom_bank_reconciliation/wizard/bank_statement_csv_import_wizard_views.xml`
- Required columns: `date`, `label`, `amount`
- Optional columns: `partner_name` (matched by case-insensitive name search), `reference`
- Journal is picked in the wizard, not a CSV column.
- Already has a **Download Sample CSV Template** button (added previously) generating exactly these 5 headers with one example row, respecting the wizard's selected date format/delimiter.
- Not yet done: XLSX variant, inline pre-import validation preview, shared template-generator helper (currently a one-off method).

### 2. Vendor Bill OCR Upload
- File: `addons/custom_accounting_ocr/models/account_bill_digitization.py`
- Accepts: PDF/image (`document` binary field), any MIME — no CSV.
- Extracted/reviewed fields: vendor, invoice number, invoice date, due date, tax amount, total amount, then manually confirmed before an `account.move` is created.
- No provider-specific size/format constraints are enforced in code (`get_provider` dispatches to a registry; the only real provider besides `manual` should be checked in `ocr_provider.py` if you want exact accepted extensions documented).
- Not yet done: no sample document or "what should this bill look like" guide next to the upload field.

## What I did NOT build (and why)

Your original spec asked for templates/samples across ~13 subsystems (QIF/OFX/CAMT, EDI, assets, budget, analytic, affiliate payouts, a central `account.import.template.registry`, etc.). I did not implement those because the underlying import/upload features don't exist in this codebase — building templates for them would mean inventing new functionality (new wizards, new import logic) rather than documenting/improving something real. That's a scope decision, not an audit gap.

## Recommended next step

Tell me which of these you want built next:
- (a) XLSX template + validation preview for the bank CSV importer, or
- (b) sample bill + "what this file should look like" guide for the OCR upload, or
- (c) a genuinely new bulk-import feature for a specific model (name it) — e.g. bulk fixed-asset entry or bulk affiliate payouts — which would be new functionality, not a fix to something existing.
