from odoo import _, api, fields, models
from odoo.exceptions import UserError

REVENUE_TYPES = ('income', 'income_other')
EXPENSE_TYPES = ('expense', 'expense_depreciation', 'expense_direct_cost')


class AccountBudget(models.Model):
    _name = 'account.budget'
    _description = 'Budget'
    _order = 'date_from desc, name'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Department / Project / Branch / Cost Center',
        help="The analytic account this budget scopes actuals to.")

    budget_type = fields.Selection([
        ('revenue', 'Revenue Budget'),
        ('expense', 'Expense Budget'),
    ], required=True, default='expense')
    period_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], required=True, default='yearly')
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1, month=1))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=31, month=12))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft')

    budgeted_amount = fields.Monetary(required=True, currency_field='currency_id')
    revision_ids = fields.One2many('account.budget.revision', 'budget_id', string='Revision History')
    committed_amount = fields.Monetary(
        currency_field='currency_id',
        help="Manually enter known committed spend (e.g. open purchase orders) not yet posted as actuals.")
    actual_amount = fields.Monetary(compute='_compute_actual_amount', store=True, currency_field='currency_id')
    remaining_amount = fields.Monetary(compute='_compute_variance', store=True, currency_field='currency_id')
    variance_amount = fields.Monetary(compute='_compute_variance', store=True, currency_field='currency_id')
    variance_percent = fields.Float(compute='_compute_variance', store=True)

    @api.depends('analytic_account_id', 'date_from', 'date_to', 'budget_type', 'company_id')
    def _compute_actual_amount(self):
        for budget in self:
            if not budget.analytic_account_id:
                budget.actual_amount = 0.0
                continue
            account_types = REVENUE_TYPES if budget.budget_type == 'revenue' else EXPENSE_TYPES
            lines = self.env['account.move.line'].search([
                ('move_id.company_id', '=', budget.company_id.id),
                ('move_id.state', '=', 'posted'),
                ('date', '>=', budget.date_from),
                ('date', '<=', budget.date_to),
                ('account_id.account_type', 'in', account_types),
                ('analytic_distribution', '!=', False),
            ])
            total = 0.0
            for line in lines:
                percentage = (line.analytic_distribution or {}).get(str(budget.analytic_account_id.id))
                if not percentage:
                    continue
                amount = -line.balance if budget.budget_type == 'revenue' else line.balance
                total += amount * (percentage / 100.0)
            budget.actual_amount = total

    @api.depends('budgeted_amount', 'actual_amount', 'committed_amount')
    def _compute_variance(self):
        for budget in self:
            budget.remaining_amount = budget.budgeted_amount - budget.actual_amount - budget.committed_amount
            budget.variance_amount = budget.actual_amount - budget.budgeted_amount
            budget.variance_percent = (
                (budget.variance_amount / budget.budgeted_amount * 100.0) if budget.budgeted_amount else 0.0
            )

    def action_confirm(self):
        for budget in self:
            if not budget.analytic_account_id:
                raise UserError(_("Set an analytic account before confirming this budget."))
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def write(self, vals):
        old_amounts = {}
        if 'budgeted_amount' in vals:
            old_amounts = {
                budget.id: budget.budgeted_amount
                for budget in self if budget.state == 'confirmed'
            }
        result = super().write(vals)
        if old_amounts:
            new_amount = vals['budgeted_amount']
            for budget in self.browse(old_amounts.keys()):
                old_amount = old_amounts[budget.id]
                if old_amount != new_amount:
                    self.env['account.budget.revision'].create({
                        'budget_id': budget.id,
                        'old_amount': old_amount,
                        'new_amount': new_amount,
                    })
        return result
