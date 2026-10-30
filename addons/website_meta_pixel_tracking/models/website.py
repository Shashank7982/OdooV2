from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    meta_pixel_id = fields.Char(string='Meta Pixel ID')
