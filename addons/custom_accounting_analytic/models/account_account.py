from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    require_analytic_distribution = fields.Boolean(
        string='Require Analytic Account',
        help="If set, journal items posted on this account must have an analytic distribution.")
