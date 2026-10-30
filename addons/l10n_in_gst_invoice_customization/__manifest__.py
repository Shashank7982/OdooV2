{
    'name': 'GST Invoice Customization',
    'category': 'Accounting/Localizations',
    'summary': 'Full GST-compliant invoice print: seller/customer KYC, shipping, discounts, bank/UPI QR, signature, terms',
    'description': """
GST Invoice Customization
==========================
Extends Odoo's Indian GST invoicing (l10n_in) with everything needed for a
complete, print-ready GST tax invoice:

- Seller KYC: PAN, CIN, IEC, TAN, FSSAI, contact person, bank details, UPI ID
- Customer KYC: PAN (mandatory), CIN, IEC, TAN, FSSAI, contact person
- Shipping/transport section integrated with the Shiprocket addon, if installed
- Per-line HSN/SAC, discount amount, taxable value, CGST/SGST/IGST breakup
- Separate Shipping Charges section with its own GST breakup
- Coupon, manual discount, and affiliate discount (customer-safe fields only)
- Bank details + generated UPI QR code
- Authorized signature + company stamp block
- Mandatory GSTIN (company) / PAN (customer) validation before posting

Does not modify or remove any existing l10n_in report content — everything
here is added via view/model inheritance.
""",
    'version': '1.0',
    'depends': ['l10n_in', 'account', 'sale', 'sale_loyalty', 'website_sale_affiliate'],
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/report_layout_invoice.xml',
    ],
    'license': 'LGPL-3',
}
