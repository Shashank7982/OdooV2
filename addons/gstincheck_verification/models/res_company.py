from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    gst_check_enabled = fields.Boolean(string='Enable GSTIN Verification (gstincheck.co.in)', default=False)
    gst_check_api_key = fields.Char(string='gstincheck.co.in API Key', copy=False)
