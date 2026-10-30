from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    recurring_entry_id = fields.Many2one(
        'account.recurring.entry', string='Generated From Recurring Template',
        readonly=True, copy=False,
    )
