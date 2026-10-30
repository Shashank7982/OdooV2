# Custom Accounting Release Checklist

This checklist is for the accounting suite installed under `D:\Odoo18\addons`.

## Modules in the release

- `custom_accounting_completion`
- `custom_bank_reconciliation`
- `custom_accounting_security`

The release also relies on the existing accounting, sales, purchase, stock,
cash, reports, budget, deferred, asset, OCR, Indian-reporting, and core
modules listed in the module manifests.

## Deployment sequence

1. Stop the Odoo service before changing Python/XML files.
2. Back up the PostgreSQL database and filestore.
3. Copy the three modules from the release branch into `D:\Odoo18\addons`.
4. Start Odoo with the normal `odoo.conf`.
5. Upgrade in this order:
   `custom_bank_reconciliation`, `custom_accounting_completion`,
   `custom_accounting_security`.
6. Refresh the browser assets and sign in with an Accounting Manager user.

## Acceptance smoke tests

- Preview a valid CSV and XLSX bank file; verify rows and totals before import.
- Preview a file containing one invalid row; verify the Import button is
  blocked and no valid row is created.
- Import the same file twice; verify duplicates are listed and skipped.
- Create and activate a sales contract, then release one linked sales order.
- Validate a waybill number and verify validator and validation time are set.
- Post a customer invoice with a missing product line; verify posting is
  rejected with a useful validation error.
- Complete and lock a year close, then prepare the next-year opening package.
- Sign in as Auditor and verify completion records are readable but not
  createable, editable, or deletable.

## External integration boundary

GST/e-invoice/e-way-bill submission remains an external provider/credential
boundary. This release stores the workflow boundary and validation metadata;
it does not invent a GST portal credential or silently submit production tax
documents. Configure and test the chosen provider separately.

## Post-release checks

- Confirm scheduled jobs are running.
- Confirm accounting lock dates and company fiscal year are correct.
- Confirm the database backup can be restored in a non-production database.
- Keep the upgrade log and test result with the release record.
