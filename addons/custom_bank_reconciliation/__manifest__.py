{
    'name': 'Custom Bank Reconciliation',
    'category': 'Accounting/Accounting',
    'summary': 'CSV bank statement import and unmatched transaction queue for Community',
    'description': """
Custom Bank Reconciliation
=============================
Part of custom_full_accounting.

Odoo Community already includes the reconciliation engine itself
(account.reconcile.model, account.bank.statement.line manual/partial/full
reconciliation, auto-matching by partner/amount/reference) — this module
does not rebuild that. What Community is missing is a way to get bank
transactions INTO the system from a file: this module adds a CSV bank
statement import wizard, plus a simple "Unmatched Transactions" queue view.

OFX/QIF/CAMT import are NOT implemented — CSV only. This module does not
claim or provide live bank synchronization.
""",
    'version': '1.0',
    'depends': ['account', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bank_statement_csv_import_wizard_views.xml',
        'views/account_bank_statement_line_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
