from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    meta_pixel_id = fields.Char(
        related='website_id.meta_pixel_id', readonly=False,
    )
