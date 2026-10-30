from odoo import fields, models


class MetaPixelEvent(models.Model):
    _name = 'meta.pixel.event'
    _description = 'Meta Pixel Event Log'
    _order = 'create_date desc'
    _rec_name = 'event_type'

    event_type = fields.Selection([
        ('page_view', 'Page View'),
        ('purchase', 'Purchase'),
        ('lead', 'Lead'),
    ], required=True)
    website_id = fields.Many2one('website', string='Website')
    url = fields.Char()
    value = fields.Monetary()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    partner_id = fields.Many2one('res.partner', string='Contact')
    sale_order_id = fields.Many2one('sale.order', string='Order')
    lead_id = fields.Many2one('crm.lead', string='Lead')
