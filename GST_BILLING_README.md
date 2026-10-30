# GST Billing — Odoo 18 (Indian Localization)

This isn't a custom addon — it's Odoo's own built-in Indian GST toolkit
(`l10n_in*`), installed and configured in `odoo18db`. This file documents
what's active, where to find it, and the step-by-step workflow for each
feature so you don't have to rediscover it later.

## Status
All 14 modules installed with zero errors. A demo Indian company
("IN Company", Gujarat, GSTIN `24DUMMY1234AAZA`) exists as a ready sandbox —
your real US-based companies (My Company - San Francisco/Chicago) were left
untouched, since converting an existing company with posted journal entries
to a different country/chart of accounts isn't a safe operation.

**Full Accounting app (`account_accountant`) is not available** — this
instance is Odoo Community, and that module is Enterprise-only. Every GST
feature below runs through the **Invoicing** app instead, which has the same
underlying capability for billing/tax/reporting purposes.

## Modules installed

| Module | What it gives you |
|---|---|
| `l10n_in` | Indian Chart of Accounts, CGST/SGST/IGST tax setup, GSTIN + HSN/SAC fields |
| `l10n_in_sale` / `l10n_in_purchase` / `l10n_in_stock` | GST-formatted Sale, Purchase, Stock reports (GSTR-prep) |
| `l10n_in_sale_stock` / `l10n_in_purchase_stock` | GST fields carried through delivery/receipt documents |
| `l10n_in_edi` | E-invoicing — IRN + QR code submission to the govt portal |
| `l10n_in_edi_ewaybill` | E-way bill generation from invoices |
| `l10n_in_ewaybill_stock` | E-way bill generation directly from inventory transfers |
| `l10n_in_ewaybill_port` | Port code support for Air/Sea e-way bills |
| `l10n_in_gstin_status` | Live GSTIN validity check from a contact record |
| `l10n_in_pos` | GST tax handling inside Point of Sale |
| `l10n_in_withholding` / `l10n_in_withholding_payment` | TDS/TCS deduction on invoices and payments |

## How to switch into the GST company

Top-right corner, next to your profile avatar → click the company name →
select **"IN Company"**. Everything below assumes you're working inside
this company, since GST fields only activate for an India-localized company.

If you don't see a company switcher at all, multi-company mode isn't
enabled for your user — go to **Settings → Users & Companies → Users**,
open your user, and check "IN Company" under **Allowed Companies**.

---

## Feature-by-feature workflow

### 1. GST-compliant invoicing (core `l10n_in`)
**Where:** Invoicing app → Customers → Invoices

**One-time setup:**
- On each customer/vendor contact: set **GSTIN** and **State** — this is
  what determines CGST+SGST (same state) vs IGST (different state)
- On each product: set the **HSN/SAC Code** (Sales tab)

**Workflow:**
1. New Invoice → pick customer (GSTIN/state auto-fill from their contact)
2. Add product lines — GST tax auto-applies based on HSN code + buyer/seller
   state comparison
3. Confirm/post — this is a fully compliant GST invoice, PDF-printable with
   the tax breakup shown

### 2. GSTIN status verification (`l10n_in_gstin_status`)
**Where:** any Contact record with a GSTIN set, or directly on an invoice

**Workflow:** open the contact → there's a verify/check action next to the
GSTIN field → calls the government's live GSTIN lookup → confirms the
number is real/active before you invoice them.

### 3. E-Invoicing (`l10n_in_edi`)
**Where:** Settings → Accounting (or the Invoicing app's config) → Indian
E-invoice section

**One-time setup:** you need an API username/password from the government
e-invoice portal, obtained through the GSP ("Tera Software Limited" is what
Odoo integrates with). Enter those credentials in Settings.

**Workflow:**
1. Post a customer invoice as normal
2. A **"Send E-invoice"** action appears on posted invoices
3. Submitting returns an **IRN (Invoice Reference Number) + signed QR code**
4. Both print automatically on the invoice PDF from then on

Only legally required above the government's e-invoicing turnover
threshold — optional below that, but the module works regardless.

### 4. E-Way Bill (`l10n_in_edi_ewaybill`, `l10n_in_ewaybill_stock`, `l10n_in_ewaybill_port`)
**Where:** on a posted invoice, or directly from an Inventory transfer

**One-time setup:** same GSP-issued API credentials as e-invoicing, entered
in Settings.

**Workflow:**
1. On a posted invoice **or** a stock transfer → **"Generate E-way Bill"**
2. Fill transport details: vehicle number, transporter ID, distance
3. Submit → returns an E-way Bill number, valid for that specific trip
4. Air/Sea transport modes get a port-code field (`l10n_in_ewaybill_port`)

Legally required for goods movement above ₹50,000 in value.

### 5. TDS / TCS — Tax Deducted/Collected at Source (`l10n_in_withholding`, `l10n_in_withholding_payment`)
**Where:** Accounting → Vendors → Payments (and on invoices)

**Workflow:** when recording a vendor payment, a withholding-tax wizard
appears letting you apply the correct TDS section and rate at payment time.
Relevant if your business deducts TDS alongside collecting GST — common for
Indian B2B vendors above the deduction threshold.

### 6. GST reports (`l10n_in_sale`, `l10n_in_purchase`, `l10n_in_stock`)
**Where:** Invoicing → Reporting, or the Sales/Purchase/Inventory apps'
reporting menus

**Workflow:** these generate GSTR-1-ready breakdowns — B2B, B2C, HSN
summary — for a given period. **Odoo does not auto-file this to the GST
portal** — export the report and either file manually or hand it to your
CA/filing tool.

### 7. GST in Point of Sale (`l10n_in_pos`)
**Where:** Point of Sale app, once a POS session is opened under IN Company

**Workflow:** GST tax splits (CGST/SGST/IGST) apply automatically on POS
orders the same way they do on invoices — no separate configuration beyond
what's already set on products/customers.

---

## What's tested vs. not

| Item | Status |
|---|---|
| Module install (all 14) | ✅ Verified — zero errors, `odoo18db` |
| Demo "IN Company" exists with Indian CoA | ✅ Verified |
| GST invoice creation, CGST/SGST/IGST auto-split | Not yet tested end-to-end |
| GSTIN status check | Not yet tested (needs live GSTIN) |
| E-invoicing | Not tested — requires GSP credentials you haven't obtained yet |
| E-way bill | Not tested — same requirement |
| TDS/TCS | Not tested |
| GST reports | Not tested |

## Known caveats
- **No Enterprise Accounting app** — bank sync, drag-and-drop reconciliation,
  and interactive dynamic financial reports aren't available in this
  Community setup. None of that blocks GST billing itself.
- **E-invoice and E-way bill need paid GSP credentials** you'd obtain
  directly from the government portal — nothing here can get those for you.
- **GSTR filing itself is manual** — Odoo prepares the data, doesn't submit
  the return.
- Full company creation (a real Indian company with your actual GSTIN,
  address, bank details) hasn't been done — only the auto-generated demo
  "IN Company" exists so far. Ask if you want a proper company set up
  instead of/alongside the demo one.
