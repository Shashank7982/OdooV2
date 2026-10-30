{
    'name': 'Custom Accounting Deferred Revenue/Expense',
    'category': 'Accounting/Accounting',
    'summary': 'Deferred revenue and expense recognition schedules with automatic monthly journal entries',
    'description': """
Custom Accounting Deferred Revenue/Expense
==============================================
Part of custom_full_accounting. Built from scratch (not present in this
Community instance otherwise).

- Deferred revenue and deferred expense schedules, with start/end date
- Automatic even monthly recognition amount
- A daily cron posts recognition entries once their date is reached
- Remaining balance tracked automatically
- Early termination (recognizes remaining balance immediately)
- Manual per-line amount adjustment before posting
""",
    'version': '1.0',
    'depends': ['account', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/account_deferred_schedule_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
