{
    'name': 'Custom Accounting Security',
    'category': 'Accounting/Accounting',
    'summary': 'Cross-cutting security groups and field-level protections for the custom_full_accounting suite',
    'description': """
Custom Accounting Security
==============================
Part of custom_full_accounting. Adds the suite-wide access control layer
required by the accounting spec on top of the 11 functional modules:

- Groups: Accounting User, Accounting Manager, Finance Controller,
  Auditor (read-only), CFO / Admin
- Model access overrides for the operational and report models added by
  the 11 modules, scoped to these groups
- Field-level protection on bank account numbers (res.partner.bank),
  restricted to Finance Controller / CFO and above

This module only adds groups, access rows, and an inheriting view — it
does not modify any Odoo core file.
""",
    'version': '1.0',
    'depends': [
        'account',
        'custom_accounting_core',
        'custom_accounting_reports',
        'custom_bank_reconciliation',
        'custom_accounting_analytic',
        'custom_accounting_budget',
        'custom_accounting_assets',
        'custom_accounting_deferred',
        'custom_accounting_followup',
        'custom_accounting_ocr',
        'custom_accounting_indian',
        'custom_accounting_dashboard',
        'custom_accounting_cash',
        'custom_accounting_completion',
    ],
    'data': [
        'security/accounting_groups.xml',
        'security/ir.model.access.csv',
        'views/account_move_workflow_views.xml',
        'views/res_partner_bank_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_accounting_security/static/src/js/workflow_buttons.js',
        ],
    },
    'license': 'LGPL-3',
}
