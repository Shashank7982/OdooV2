from odoo import fields, models


class AccountBudgetRevision(models.Model):
    _name = 'account.budget.revision'
    _description = 'Budget Revision History'
    _order = 'date desc, id desc'

    budget_id = fields.Many2one('account.budget', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one(related='budget_id.currency_id')
    old_amount = fields.Monetary(currency_field='currency_id')
    new_amount = fields.Monetary(currency_field='currency_id')
    note = fields.Char()
