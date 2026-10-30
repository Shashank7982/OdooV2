{
    'name': 'GSTIN Verification (gstincheck.co.in)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Verify Indian GSTINs live via the free gstincheck.co.in GST lookup API',
    'description': """
GSTIN Verification (gstincheck.co.in)
========================================
Adds a "Verify GSTIN" action to Indian contacts using gstincheck.co.in's free
GST lookup API (https://sheet.gstincheck.co.in/check/<api_key>/<gstin>) —
a single API-key GET request, no OAuth/token exchange, no test/production
split like Sandbox.co.in. Live GSTN data, not dummy/canned test data.

Stores the returned legal name, trade name, PAN (derived from the GSTIN
itself), registered address, registration status/date, state and the raw
API response. Never marks a GSTIN verified when the call fails or the GSTIN
isn't found.

Replaces the gstin_sandbox_verification module (that one used a paid,
test/production-split provider); this module should not be installed
alongside it, since both add the same "Verify GSTIN" button/fields to
res.partner.
""",
    'depends': ['l10n_in', 'l10n_in_gst_invoice_customization'],
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
