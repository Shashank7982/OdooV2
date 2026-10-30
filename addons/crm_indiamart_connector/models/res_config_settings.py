from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    indiamart_enabled = fields.Boolean(
        related='company_id.indiamart_enabled', readonly=False,
    )
    indiamart_crm_key = fields.Char(
        related='company_id.indiamart_crm_key', readonly=False,
    )
