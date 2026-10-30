{
    'name': 'Contact Classification',
    'category': 'Contacts',
    'summary': 'Contact type selection (Employee/Vendor/Customer/Affiliate/Consultant/Other) with type-specific layout',
    'description': """
Contact Classification
=======================
Extends Contacts so every new contact is first classified by type:
Employee, Vendor, Customer, Affiliate/Commission Partner, Consultant, or Other
(Customers get an additional D2C/Retailer/Distributor/Manufacturer/Wholesaler
category). The contact form then shows only the fields and smart buttons
relevant to that type, while common fields (name, phone, email, address, tax
info, bank details) always remain available.

Reuses core Odoo data wherever it already exists instead of duplicating it:
- Vendor/Customer: native purchase/sale history, payable/receivable
  (credit/debit), GST fields (l10n_in), payment terms, credit limit.
- Employee: links to the existing hr.employee record (department, job,
  manager, attendance, expenses live there).
- Affiliate: links to the existing sale.affiliate record (commission rate,
  history, payouts).
- Consultant: adds lightweight service/contract fields and reuses the
  vendor-bill (payable) picture, since consultants are typically paid like
  vendors.

Does not restrict who can create contacts elsewhere in Odoo (quick-create
from a dropdown still works) - it targets the main Contacts app browse/create
flow specifically, which is where this classification decision belongs.
""",
    'version': '1.0',
    'depends': [
        'contacts', 'account', 'sale', 'purchase', 'custom_accounting_affiliate',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/res_partner_menu.xml',
        'wizard/res_partner_type_wizard_views.xml',
    ],
    'license': 'LGPL-3',
}
