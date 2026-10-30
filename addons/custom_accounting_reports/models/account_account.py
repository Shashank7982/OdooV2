from odoo import api, fields, models

INVESTING_TYPES = ('asset_fixed', 'expense_depreciation')
FINANCING_TYPES = ('liability_non_current', 'equity', 'equity_unaffected')


class AccountAccount(models.Model):
    _inherit = 'account.account'

    cash_flow_category = fields.Selection([
        ('operating', 'Operating'),
        ('investing', 'Investing'),
        ('financing', 'Financing'),
        ('none', 'Not Applicable'),
    ], string='Cash Flow Category', compute='_compute_cash_flow_category', store=True, readonly=False)

    @api.depends('account_type')
    def _compute_cash_flow_category(self):
        for account in self:
            if account.cash_flow_category:
                continue
            if account.account_type in INVESTING_TYPES:
                account.cash_flow_category = 'investing'
            elif account.account_type in FINANCING_TYPES:
                account.cash_flow_category = 'financing'
            elif account.account_type in ('asset_cash',):
                account.cash_flow_category = 'none'
            else:
                account.cash_flow_category = 'operating'
