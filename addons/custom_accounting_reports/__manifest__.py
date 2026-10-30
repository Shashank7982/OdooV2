{
    'name': 'Custom Accounting Financial Reports',
    'category': 'Accounting/Accounting',
    'summary': 'Trial Balance, P&L, Balance Sheet, Aged Receivable/Payable — built from scratch for Community',
    'description': """
Custom Accounting Financial Reports
======================================
Part of custom_full_accounting. Odoo Community has no equivalent of
Enterprise's `account_reports` module — this builds the core financial
statements from scratch using standard `account.move.line` queries via the
ORM (no raw SQL).

Reports:
- Trial Balance
- Profit and Loss
- Balance Sheet
- General Ledger
- Cash Flow Statement
- Journal Audit
- Aged Receivable
- Aged Payable

Plus pivot/graph "Advanced Analysis" actions on core account.move.line /
account.payment for Invoice Analysis, Payment Analysis, Revenue by
Customer, Expense by Vendor, and Product Margin (Community has no
account.invoice.report model, so these are built directly on
account.move.line).

All support date range, company (including multi-company consolidation),
and journal filters, with drill-down from a report line to its underlying
journal items, PDF export, and CSV export.
""",
    'version': '1.0',
    'depends': ['account', 'custom_accounting_core', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/financial_report_wizard_views.xml',
        'wizard/aged_partner_report_wizard_views.xml',
        'report/financial_report_templates.xml',
        'views/analysis_actions.xml',
        'views/bank_transaction_reports.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
