{
    'name': 'Custom Accounting Analytic',
    'category': 'Accounting/Accounting',
    'summary': 'Department/Branch/Cost Center plans, mandatory analytic rule, profitability report',
    'description': """
Custom Accounting Analytic
=============================
Part of custom_full_accounting. Odoo Community already includes
account.analytic.account, account.analytic.plan, and analytic
distribution (the analytic module) — this does not rebuild those.

Adds:
- Pre-seeded analytic plans for Department, Project, Branch, Cost Center,
  Profit Center (so you can start tagging entries immediately)
- A "Require Analytic Account" flag on account.account, enforced when
  posting journal entries
- A Profitability report (revenue/cost/margin by analytic account)
""",
    'version': '1.0',
    'depends': ['analytic', 'account', 'custom_accounting_core', 'custom_accounting_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/analytic_plan_data.xml',
        'views/account_account_views.xml',
        'wizard/profitability_report_wizard_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
