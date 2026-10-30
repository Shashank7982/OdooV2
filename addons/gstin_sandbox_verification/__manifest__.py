{
    'name': 'GSTIN Sandbox Verification',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Verify Indian GSTINs through Sandbox test or production API',
    'description': """
GSTIN Sandbox Verification
==========================
Adds a Verify GSTIN action to Indian contacts and stores the returned legal
name, trade name, PAN, registration status, registration date and response
metadata. Supports Sandbox's free test environment and billed production
environment. The module never marks a GSTIN verified when the API call fails.
""",
    'depends': ['l10n_in', 'l10n_in_gst_invoice_customization'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
