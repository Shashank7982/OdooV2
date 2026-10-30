from odoo import models, fields


class SaleAffiliate(models.Model):
    _name = 'sale.affiliate'
    _description = 'Sales Affiliate'

    name = fields.Char(string='Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    key = fields.Char(string='Key Code', required=True, copy=False)

    _sql_constraints = [
        ('key_uniq', 'unique(key)', 'The affiliate key must be unique!'),
    ]
