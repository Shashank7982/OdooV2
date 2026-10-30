{
    'name': 'Custom Accounting Budget',
    'category': 'Accounting/Accounting',
    'summary': 'Budgets by analytic account with actual/committed/variance tracking',
    'description': """
Custom Accounting Budget
============================
Part of custom_full_accounting. Built from scratch (Enterprise's
account_budget is not present in this Community instance).

- Annual/monthly/quarterly budgets, scoped to an analytic account
  (department, project, branch, cost center, or profit center)
- Draft -> Confirmed -> Done approval workflow
- Budgeted amount vs. Actual amount (computed from posted account.move.line
  matching the budget's analytic account, date range, and account type)
- Variance and Variance % computed automatically
- Budget vs Actual list/pivot view
""",
    'version': '1.0',
    'depends': ['analytic', 'account', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_budget_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
