from odoo import fields, models


class AccountAssetCategory(models.Model):
    _name = 'account.asset.category'
    _description = 'Asset Category'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    asset_type = fields.Selection([
        ('fixed', 'Fixed Asset'),
        ('intangible', 'Intangible Asset'),
    ], required=True, default='fixed', help="Every asset created under this category is classified as this type.")
    method = fields.Selection([
        ('linear', 'Straight-Line'),
        ('declining', 'Declining Balance'),
    ], required=True, default='linear')
    duration_months = fields.Integer(string='Duration (Months)', default=36, help="Used for the straight-line method.")
    declining_rate = fields.Float(string='Declining Rate (% per year)', default=20.0, help="Used for the declining-balance method.")

    asset_account_id = fields.Many2one('account.account', string='Fixed Asset Account', required=True)
    depreciation_account_id = fields.Many2one('account.account', string='Accumulated Depreciation Account', required=True)
    expense_account_id = fields.Many2one('account.account', string='Depreciation Expense Account', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain="[('type', '=', 'general')]")

    gain_account_id = fields.Many2one(
        'account.account', string='Gain on Sale Account',
        domain="[('account_type', 'in', ('income', 'income_other'))]",
        help="Used to book gain when sale price exceeds book value. Falls back to the Depreciation Expense Account if unset.")
    loss_account_id = fields.Many2one(
        'account.account', string='Loss on Sale Account',
        domain="[('account_type', 'in', ('expense', 'expense_depreciation', 'expense_direct_cost'))]",
        help="Used to book loss when sale price is below book value. Falls back to the Depreciation Expense Account if unset.")
    revaluation_account_id = fields.Many2one(
        'account.account', string='Revaluation Reserve Account',
        domain="[('account_type', 'in', ('equity', 'equity_unaffected'))]",
        help="Equity account used as the contra-entry when revaluing assets in this category.")
