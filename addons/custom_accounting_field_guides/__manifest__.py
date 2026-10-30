{
    'name': 'Accounting Field & Upload Templates',
    'category': 'Accounting/Accounting',
    'summary': 'Downloadable field guides (form-only features) and data templates (importable uploads) across accounting/GST/affiliate modules',
    'description': """
Accounting Field & Upload Templates
====================================
Adds two kinds of downloadable reference files, generated from the actual
Odoo model definitions so they never drift from the real screens:

1. Field Guides (XLSX) — for form-only accounting features (no file import
   exists). Lists every relevant field, its type, required/optional status,
   allowed values, and an example, plus a blank "Value to be entered"
   column so an admin can hand this to staff/accountant/customer before
   data entry. Clearly marked "Reference Template - Not for Upload".

2. Data Templates (CSV/XLSX) — for features that genuinely accept a file
   upload (e.g. Bank Statement CSV import), matching the exact headers the
   importer parses.

Entries are registered in Accounting > Configuration > Field & Upload
Guides. Each entry stores only a model name (text) and a curated list of
field names, so this module has no hard dependency on the other custom
accounting/affiliate/GST modules — a guide simply reports a clear error if
its target module isn't installed.
""",
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/field_guide_views.xml',
        'data/field_guide_data.xml',
    ],
    'license': 'LGPL-3',
}
