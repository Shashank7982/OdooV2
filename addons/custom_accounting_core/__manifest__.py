{
    'name': 'Custom Accounting Core',
    'category': 'Accounting/Accounting',
    'summary': 'Community-compatible core accounting extensions: recurring entries, opening balances, duplicate bill detection',
    'description': """
Custom Accounting Core
========================
Phase 1 of the custom_full_accounting suite — a from-scratch, Community-
compatible foundation for accounting features normally only in Odoo
Enterprise Accounting. Built entirely with standard Odoo APIs; no
Enterprise code copied or referenced.

This module deliberately does NOT reimplement things Odoo Community
`account` already provides (chart of accounts, journals, journal entries,
debit/credit validation, lock dates, draft/posted/cancelled states, audit
trail via mail.thread, reversing entries via account.move.reversal,
multi-company/multi-currency, partner receivable/payable, and duplicate
vendor bill detection — all already core). It only adds what's actually
missing:

- Recurring journal entries (template + frequency + cron)
- Opening balance wizard (guided, balance-checked)

Depends only on core `account` (+ `l10n_in` for Indian-context field
compatibility) — does not modify any existing invoice, GST, or Shiprocket
functionality.
""",
    'version': '1.0',
    'application': True,
    'sequence': 5,
    'depends': ['account'],
    'post_init_hook': 'post_init_hook',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/exchange_rate_settings_views.xml',
        'data/res_currency_data.xml',
        'data/product_pricelist_data.xml',
        'data/expense_entry_sequence.xml',
        'views/account_recurring_entry_views.xml',
        'views/account_move_views.xml',
        'views/res_users_views.xml',
        'wizard/account_opening_balance_wizard_views.xml',
        'views/expense_entry_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
