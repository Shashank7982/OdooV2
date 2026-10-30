from odoo import models, fields, api


class AffiliateCommission(models.Model):
    _name = 'affiliate.commission'
    _description = 'Affiliate Commission'
    _order = 'create_date desc'

    affiliate_id = fields.Many2one(
        'sale.affiliate', string='Affiliate', required=True, ondelete='cascade',
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', required=True, ondelete='restrict',
    )
    amount = fields.Monetary(string='Commission Amount', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    rate = fields.Float(string='Commission Rate (%)')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)

    def action_confirm(self):
        self.filtered(lambda c: c.state == 'draft').write({'state': 'confirmed'})

    def action_cancel(self):
        self.filtered(lambda c: c.state == 'draft').write({'state': 'cancelled'})
