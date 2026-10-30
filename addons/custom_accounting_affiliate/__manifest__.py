{
    'name': 'Custom Accounting Affiliate Bridge',
    'category': 'Accounting/Accounting',
    'summary': 'Links affiliate commissions and payouts into real accounting payments and the accounting dashboard',
    'description': """
Custom Accounting Affiliate Bridge
======================================
Part of custom_full_accounting. Bridges the existing `website_sale_affiliate_custom`
program (affiliate.commission / affiliate.withdrawal) into actual accounting records:

- "Mark as Paid" on an affiliate withdrawal now creates and posts a real
  `account.payment` (outbound, to the affiliate's partner) instead of just
  flipping a status flag — so affiliate payouts show up in Accounting like
  any other vendor payment, with a proper payable trail.
- Adds affiliate commission KPIs (earned, paid, pending payable) to the
  Custom Accounting dashboard.
- Adds an "Affiliates" menu inside the Custom Accounting app.

Does not modify any Odoo core file or the existing affiliate program logic
beyond the payment-creation hook on withdrawal payment.
""",
    'version': '1.0',
    'depends': ['account', 'custom_accounting_core', 'custom_accounting_dashboard', 'website_sale_affiliate_custom'],
    'data': [
        'security/ir.model.access.csv',
        'views/affiliate_withdrawal_views.xml',
        'views/accounting_dashboard_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
