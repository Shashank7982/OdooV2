from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    indiamart_enabled = fields.Boolean(string='Enable Indiamart Lead Sync')
    indiamart_crm_key = fields.Char(string='Indiamart CRM Key')
    indiamart_last_pull = fields.Datetime(
        string='Indiamart Last Pull (UTC)',
        help='Timestamp up to which leads have already been fetched. '
             'Used as the start of the next pull window.',
    )
