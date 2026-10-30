{
    'name': 'Custom Accounting Vendor Bill Digitization (OCR)',
    'category': 'Accounting/Accounting',
    'summary': 'Pluggable OCR provider architecture for vendor bill digitization, manual approval required',
    'description': """
Custom Accounting Vendor Bill Digitization (OCR)
=====================================================
Part of custom_full_accounting.

Provides a pluggable OCR provider architecture (Python abstract interface)
so any OCR service can be wired in later without changing this module's
core logic. No paid OCR service is hard-coded or called by default — the
built-in "Manual / No Provider" option simply lets you attach a bill and
type in the extracted fields yourself.

Workflow: upload a PDF/image -> (optional) run through a configured
provider -> review/correct every extracted field -> only then create the
actual vendor bill. Nothing is ever posted automatically from OCR output.
The original document stays attached to the resulting bill.
""",
    'version': '1.0',
    'depends': ['account', 'custom_accounting_core'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_bill_digitization_views.xml',
        'views/menu.xml',
    ],
    'license': 'LGPL-3',
}
