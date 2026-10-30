from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Website is intentionally removed in OdooV2, but cloned database views
    # still contain this stored compatibility column. Keep the field available
    # as a harmless integer so standard Sales views can render safely.
    website_id = fields.Integer(string='Website', copy=False)
