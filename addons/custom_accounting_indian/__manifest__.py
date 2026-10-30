{
    'name': 'Custom Accounting Indian GST Reports',
    'category': 'Accounting/Localizations',
    'summary': 'GSTR-1 and GSTR-3B preparation reports, built on top of the existing l10n_in GST data',
    'description': """
Custom Accounting Indian GST Reports
=======================================
Part of the custom_full_accounting suite. Does NOT reimplement GST tax
calculation, CGST/SGST/IGST splitting, e-invoicing, e-way bill, or GSTIN
verification — all of that already works via the installed l10n_in* stack.

This module only adds a reporting/aggregation layer on top of that existing
data: a GSTR-1 preparation wizard (B2B, B2C, HSN summary) and a GSTR-3B
preparation wizard (outward taxable value, tax payable by CGST/SGST/IGST),
for a selected period and company — output only, no automatic submission to
the government portal.
""",
    'version': '1.0',
    'depends': ['l10n_in', 'account', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/gstr1_report_wizard_views.xml',
        'wizard/gstr3b_report_wizard_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
