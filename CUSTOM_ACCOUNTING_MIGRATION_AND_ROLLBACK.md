# Custom Accounting Migration and Rollback

## Before migration

Create a verified PostgreSQL database backup and a copy of the Odoo filestore.
Record the current module versions and the current `D:\Odoo18` code revision.
Do not perform the upgrade while users are posting accounting entries.

## Upgrade

Run Odoo in maintenance mode and upgrade:

```text
custom_bank_reconciliation,custom_accounting_completion,custom_accounting_security
```

The completion upgrade deactivates the previous broad `base.group_user` ACL
records and the security module supplies role-specific ACLs. Existing business
records are preserved.

## Rollback

If a release must be rolled back:

1. Stop Odoo and prevent users from reconnecting.
2. Restore the pre-release database backup and filestore backup together.
3. Restore the previous code revision from the release artifact or source
   control; do not mix old code with the new database schema.
4. Start Odoo without an automatic module upgrade and perform the smoke tests.
5. Record the reason, backup identifiers, and restored code revision.

Do not delete accounting records or manually reverse database migrations to
simulate a rollback. Accounting corrections must be posted through Odoo's
normal reversal and audit trail mechanisms.

## Data safety notes

- Bank import preview rows are transient; only approved ready rows become
  statement lines.
- An import with any validation error creates no statement lines.
- Year-close opening entries carry source metadata and an idempotency key.
- Re-running a completed year carry-forward is skipped by its completion flag.
- The old duplicate nested addon directory, if present under
  `custom_accounting_completion\custom_accounting_completion`, is not loaded
  by the configured addons path and should be removed only after a separate
  backup and review.
