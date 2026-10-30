{
    'name': 'Custom Accounting Dashboard',
    'category': 'Accounting/Accounting',
    'summary': 'Accounting KPI dashboard: receivables, payables, cash, overdue, budget variance, GST',
    'description': """
Custom Accounting Dashboard
===============================
Part of custom_full_accounting. Aggregates KPIs from account, and (if
installed) custom_accounting_budget / custom_accounting_indian, into one
filterable summary view: receivables, payables, overdue invoices, bank/cash
balances, unreconciled transactions, monthly revenue/expense/profit,
GST payable/input credit, budget variance, upcoming payments/collections,
and a simple cash-flow summary.

Does not hard-depend on the budget/GST modules — degrades gracefully
(shows zero/blank for those sections) if they aren't installed.
""",
    'version': '1.0',
    'depends': ['account', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/accounting_dashboard_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
