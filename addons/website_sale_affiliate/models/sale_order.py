from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    affiliate_id = fields.Many2one('sale.affiliate', string='Referrer Affiliate')
