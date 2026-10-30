from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    preferred_currency_id = fields.Many2one(
        'res.currency',
        string='Preferred Currency',
        help="Currency used to display amounts on accounting dashboards and reports "
             "for this user. Accounting entries and invoices are still recorded and "
             "posted in the company currency; this only converts what is shown to you.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['preferred_currency_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['preferred_currency_id']
