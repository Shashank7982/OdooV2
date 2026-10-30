# GST Invoice Customization — Odoo 18 Addon

Extends Odoo's built-in Indian GST invoicing (`l10n_in`) into a complete,
print-ready GST tax invoice: seller/customer KYC, shipping/Shiprocket
integration, per-line GST breakup, shipping charges, coupon/affiliate
discounts, bank details, a real UPI QR code, authorized signature, and
mandatory-field validation.

**Nothing existing was overwritten.** Every change is additive — new fields
on `res.company`/`res.partner`/`account.move`/`account.move.line`, and the
print template is extended via XPath inheritance on top of
`account.report_invoice_document` (the same template `l10n_in` itself
extends), never replaced.

## Status — installed, tested against a real rendered PDF

Installed cleanly into `odoo18db` (202 modules, zero errors). Verified with
an actual generated PDF invoice (not just template syntax) — caught and
fixed one real bug in the process (see "Bug found and fixed" below).

## What it adds

### 1. Seller (company) KYC — `res.company`
New fields: `l10n_in_cin`, `l10n_in_iec`, `l10n_in_tan`, `l10n_in_fssai`,
`gst_invoice_contact_name`, `gst_invoice_contact_number`.
Reuses existing `vat` (GSTIN), `l10n_in_pan` (PAN, already in `l10n_in`),
and `website` — not duplicated.

**Where:** Settings → Companies → open your company → **"GST Invoice
Details"** tab (new).

### 2. Customer KYC — `res.partner`
New fields: `gst_cin`, `gst_iec`, `gst_tan`, `gst_fssai`,
`gst_contact_person`, `gst_contact_number`.
Reuses existing `vat` (GSTIN), `l10n_in_pan` (PAN), `website`.

**Where:** any Contact form — new fields appear next to the existing
GSTIN/PAN fields l10n_in already shows there.

### 3. Mandatory GSTIN / PAN validation
- **Company GSTIN** and **customer PAN** are required before a GST invoice
  (`out_invoice`/`out_refund`, company fiscal country = India) can be
  **posted**. Overrides `account.move._post()` to raise a clear `UserError`
  listing exactly what's missing, instead of a generic failure.
- A **red banner** appears on the invoice form itself (before you even try
  to post) if either is missing, via a new computed field
  `gst_missing_fields_warning`.
- **Tested**: confirmed posting is blocked with a clear message when PAN is
  missing, and succeeds once PAN is set.

### 4. Shipping / transport section (Shiprocket-integrated)
New computed fields on `account.move`: `gst_shiprocket_order_id`,
`gst_shiprocket_awb`, `gst_shiprocket_courier`, `gst_shiprocket_status`,
`gst_shiprocket_tracking_url`, `gst_shipping_contact_name`,
`gst_shipping_contact_number`.

Pulled by traversing `invoice_line_ids.sale_line_ids.order_id.picking_ids`
to find the related delivery, then reading the `delivery_shiprocket` addon's
fields (`shiprocket_shipment_id`, `carrier_tracking_ref`, etc.) **if that
addon is installed** — uses `hasattr()` guards, so this addon does not hard-
depend on `delivery_shiprocket`. If no Shiprocket data exists, falls back to
the standard Odoo shipping address (`partner_shipping_id`) and prints blank
`-` values instead of erroring.

**Tested**: renders correctly with no Shiprocket data present (all fields
show `-` safely, confirmed in the actual PDF render).

### 5. Invoice line changes
- HSN/SAC was already added by `l10n_in` — untouched.
- **Discount %** column: `l10n_in`/core only shows this column when at least
  one line has a discount; this addon forces it **always visible** on GST
  invoices regardless.
- New columns: **Discount Amount**, **Taxable Value**, **CGST**, **SGST**,
  **IGST** per line, via `account.move.line._gst_get_tax_breakup()`.
- **Bug found and fixed during testing**: the first implementation computed
  each tax's amount by re-running `tax.compute_all()` on the line's raw
  `price_unit`, which ignored the line discount entirely — a line with a
  10% discount and 5% IGST showed IGST as if there were no discount (₹50
  instead of the correct ₹45). Fixed by switching to proportionally
  splitting the line's *already-correct* `price_total - price_subtotal`
  across taxes by their rate, instead of recomputing from scratch — this
  guarantees the CGST+SGST+IGST breakdown always sums to the real tax
  amount by construction. Verified via direct computation in a live shell
  session and a re-rendered PDF: IGST now correctly shows ₹45.00.

### 6. Shipping charges (separate GST breakup, no double-counting)
`gst_shipping_taxable_amount`, `gst_shipping_tax_amount`,
`gst_shipping_total_amount` on `account.move`, computed by identifying
invoice lines whose `sale_line_ids.is_delivery` is true (the same flag core
Odoo already uses to mark a delivery/shipping charge line).

Since these are the *same* invoice lines already included in the invoice
total (not a separate/duplicate entry), there's no double-counting — the
printed "Shipping Charges" box is a **summary/breakdown view** of an amount
that's already part of the normal line table and total.

### 7. Coupon / manual / affiliate discount (customer-safe only)
`gst_coupon_code`, `gst_coupon_discount_amount`, `gst_manual_discount_amount`,
`gst_affiliate_code`, `gst_affiliate_discount_amount`, `gst_campaign_name`.

- Coupon info sourced from `sale_loyalty`'s `sale.order.applied_coupon_ids`
  and reward-line subtotals, if that module is installed.
- Affiliate info sourced from `website_sale_affiliate`'s
  `sale.order.affiliate_id` (code + discount amount derived from the
  discount % it applies to order lines).
- **`gst_campaign_name` is deliberately a plain, non-computed field** — no
  campaign concept exists in the current affiliate module, so this is left
  as a manually-settable field that can be wired up later without any
  breaking change, per the original requirement.
- **No commission, payout, or margin data is ever read or displayed** — only
  the code and the customer-facing discount amount.

### 8. Bank + UPI details
`gst_bank_name`, `gst_bank_account_holder`, `gst_bank_account_number`,
`gst_bank_ifsc`, `gst_bank_branch` (new), reuses `l10n_in_upi_id` (already
in `l10n_in`). `gst_show_bank_details` and `gst_mask_account_number` toggles
control visibility and masking (`_gst_get_masked_account_number()` shows
only the last 4 digits when enabled).

### 9. UPI QR code
`account.move.gst_upi_qr_url` builds a real `upi://pay?...` deep link (UPI
ID, merchant name, invoice number as note, INR, and optionally the invoice
amount) and renders it through Odoo's built-in `/report/barcode/` QR
endpoint — an actual scannable QR, not just logos/text.

Configurable via company fields: `gst_show_upi_qr`, `gst_qr_merchant_name`,
`gst_qr_include_amount`. If no UPI ID is configured, the field returns
`False` and the QR block doesn't render at all — no broken image.

**Known issue in this environment (not a code bug):** `web.base.url` is
currently set to a stale Cloudflare tunnel domain
(`hoping-synthesis-stylish-interactions.trycloudflare.com`) from earlier
tunnel work. wkhtmltopdf uses this URL to fetch the QR image over real HTTP
when generating a PDF, so the QR box currently renders blank in the PDF
(confirmed in testing — `HostNotFoundError`). The URL logic itself is
correct (verified it builds a valid `upi://pay?...` link); this needs
`web.base.url` pointed at a reachable host (e.g. `http://localhost:8069`
for local testing) to actually display. **I did not change this myself**
since other parts of this project may depend on that tunnel URL for
webhooks/email testing — your call.

### 10. Authorized signature
`gst_signature_image`, `gst_signatory_name`, `gst_signatory_designation`,
`gst_company_stamp` on `res.company`. Block only renders if a signature
image is actually set — confirmed hidden cleanly with no image configured
in testing.

### 11. Terms and conditions
**Deliberately not reinvented** — Odoo core already has exactly this via
`account.move.narration` (invoice-specific, editable) with a company-level
default (Settings → Invoicing → Default Terms and Conditions,
`terms_type`/`invoice_terms`). This flows through the existing `comment`
div in the base report template untouched, already paginates correctly
across multi-page invoices since it's just HTML content in the page flow.

## Files

```
l10n_in_gst_invoice_customization/
├── __manifest__.py
├── models/
│   ├── res_company.py         # seller KYC, bank, UPI/QR settings, signature
│   ├── res_partner.py         # customer KYC
│   ├── account_move.py        # shipping/Shiprocket, coupon/affiliate, shipping charges,
│   │                           # UPI QR URL, mandatory GSTIN/PAN validation
│   └── account_move_line.py   # per-line CGST/SGST/IGST breakup, shipping-line detection
└── views/
    ├── res_company_views.xml    # "GST Invoice Details" tab
    ├── res_partner_views.xml    # KYC fields on contact form
    ├── account_move_views.xml   # missing-fields warning banner
    └── report_invoice.xml       # all print-template additions (XPath only, nothing replaced)
```

## Dependencies
`l10n_in`, `account`, `sale`, `sale_loyalty`, `website_sale_affiliate`.
The last two are explicit hard dependencies so the `@api.depends()`
decorators referencing their fields (`applied_coupon_ids`, `affiliate_id`)
never break — verified both modules are actually present in this instance
before depending on them.

Shiprocket integration (`delivery_shiprocket`) is **not** a hard dependency
— accessed defensively via `hasattr()`, so this addon installs and works
fine with or without it.

## Testing performed
- ✅ Fresh install, zero errors (only two cosmetic `hasclass()` style
  warnings, non-blocking)
- ✅ Mandatory PAN validation: confirmed blocks posting with missing PAN,
  confirmed clear error message, confirmed unblocks once PAN is set
- ✅ Full PDF render with real data: company KYC block, customer PAN/CIN,
  shipping section (Shiprocket fields blank-safe), HSN/discount/GST columns,
  shipping/discount summary boxes, bank details all confirmed present and
  correctly formatted in the actual generated PDF
- ✅ Found and fixed a real CGST/SGST/IGST calculation bug (discount not
  applied) via the rendered output, not just code review
- ⚠️ UPI QR image not visually confirmed due to the `web.base.url` tunnel
  issue above — logic verified correct via the generated URL string, not
  the rendered image itself
- ❌ Not tested: authorized signature *with* an image set (only the "hidden
  when absent" case was tested), coupon discount display (no test order had
  an applied coupon), affiliate discount display (no test order had an
  active affiliate), multi-page overflow with long terms text

## Test artifact
A draft test invoice (id 65, "B2B Customer Inter State", ₹945 total, 10%
discount, IGST 5%) was created and committed to `odoo18db` during testing —
safe to delete or keep, it's a normal draft invoice.
