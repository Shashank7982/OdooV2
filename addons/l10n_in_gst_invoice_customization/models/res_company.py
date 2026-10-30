from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Seller KYC (GSTIN = vat, PAN = l10n_in_pan, both already provided by l10n_in)
    l10n_in_cin = fields.Char(string='CIN Number')
    l10n_in_iec = fields.Char(string='IEC Code')
    l10n_in_tan = fields.Char(string='TAN Number')
    l10n_in_fssai = fields.Char(string='FSSAI Number')

    gst_invoice_contact_name = fields.Char(string='Invoice Contact Person')
    gst_invoice_contact_number = fields.Char(string='Invoice Contact Number')

    # Bank details (UPI ID already provided by l10n_in as l10n_in_upi_id)
    gst_bank_name = fields.Char(string='Bank Name')
    gst_bank_account_holder = fields.Char(string='Account Holder Name')
    gst_bank_account_number = fields.Char(string='Bank Account Number')
    gst_bank_ifsc = fields.Char(string='IFSC Code')
    gst_bank_branch = fields.Char(string='Bank Branch')
    gst_show_bank_details = fields.Boolean(string='Show Bank Details on Invoice', default=True)
    gst_mask_account_number = fields.Boolean(string='Mask Account Number on Invoice', default=False)

    # UPI QR code settings
    gst_show_upi_qr = fields.Boolean(string='Show UPI QR Code on Invoice', default=True)
    gst_qr_merchant_name = fields.Char(string='UPI QR Merchant Name')
    gst_qr_include_amount = fields.Boolean(string='Include Invoice Amount in QR', default=True)

    # Authorized signature
    gst_signature_image = fields.Binary(string='Authorized Signature Image')
    gst_signatory_name = fields.Char(string='Authorized Signatory Name')
    gst_signatory_designation = fields.Char(string='Signatory Designation')
    gst_company_stamp = fields.Binary(string='Company Stamp')

    def _gst_get_masked_account_number(self):
        self.ensure_one()
        number = self.gst_bank_account_number or ''
        if not number:
            return ''
        if not self.gst_mask_account_number or len(number) <= 4:
            return number
        return ('X' * (len(number) - 4)) + number[-4:]
