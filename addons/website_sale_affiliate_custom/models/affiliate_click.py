from odoo import models, fields


class AffiliateClick(models.Model):
    _name = 'affiliate.click'
    _description = 'Affiliate Click'
    _order = 'click_date desc'

    affiliate_id = fields.Many2one(
        'sale.affiliate', string='Affiliate', required=True, ondelete='cascade',
    )
    click_date = fields.Datetime(string='Click Date', default=fields.Datetime.now, required=True)
    ip_address = fields.Char(string='IP Address')
    url = fields.Char(string='Landing URL')
    referrer_url = fields.Char(string='Referrer URL')
    converted = fields.Boolean(string='Converted', default=False)
    sale_order_id = fields.Many2one('sale.order', string='Resulting Sale Order')
