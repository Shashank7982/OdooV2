{
    'name': 'Custom Accounting Cash Transactions',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Cash transaction mode, Cash Book and Petty Cash controls',
    'description': '''
Adds the cash-management part of the custom accounting implementation:
- Cash transaction mode on sales, purchases and invoices/bills.
- Automatic cash settlement for cash-mode invoices through Odoo payments.
- Configurable cash locations and custodians.
- Petty-cash vouchers, approvals, top-ups and physical counts.
- Cash Book and Petty Cash reports based on posted accounting entries.
''',
    'depends': ['account', 'sale', 'purchase', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/cash_location_views.xml',
        'views/cash_transaction_views.xml',
        'views/petty_cash_views.xml',
        'views/cash_report_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
