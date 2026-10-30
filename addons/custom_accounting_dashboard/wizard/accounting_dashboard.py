from odoo import _, fields, models

INCOME_TYPES = ('income', 'income_other')
EXPENSE_TYPES = ('expense', 'expense_depreciation', 'expense_direct_cost')


class AccountingDashboard(models.TransientModel):
    _name = 'accounting.dashboard'
    _description = 'Accounting Dashboard'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Display Currency', required=True,
        default=lambda self: self.env.user.preferred_currency_id or self.env.company.currency_id,
        help="Amounts below are converted to this currency at today's rate for display "
             "only; accounting entries stay recorded in the company currency.")
    date_from = fields.Date(default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(default=fields.Date.context_today)

    total_receivable = fields.Monetary(readonly=True, currency_field='currency_id')
    total_payable = fields.Monetary(readonly=True, currency_field='currency_id')
    overdue_invoice_count = fields.Integer(readonly=True)
    overdue_invoice_amount = fields.Monetary(readonly=True, currency_field='currency_id')

    bank_balance = fields.Monetary(readonly=True, currency_field='currency_id')
    cash_balance = fields.Monetary(readonly=True, currency_field='currency_id')
    unreconciled_count = fields.Integer(readonly=True)

    monthly_revenue = fields.Monetary(readonly=True, currency_field='currency_id')
    monthly_expense = fields.Monetary(readonly=True, currency_field='currency_id')
    monthly_profit = fields.Monetary(readonly=True, currency_field='currency_id')

    gst_output_tax = fields.Monetary(readonly=True, currency_field='currency_id')
    gst_input_credit = fields.Monetary(readonly=True, currency_field='currency_id')
    gst_net_payable = fields.Monetary(readonly=True, currency_field='currency_id')
    gst_module_installed = fields.Boolean(readonly=True)

    budget_total = fields.Monetary(readonly=True, currency_field='currency_id')
    budget_actual = fields.Monetary(readonly=True, currency_field='currency_id')
    budget_variance = fields.Monetary(readonly=True, currency_field='currency_id')
    budget_module_installed = fields.Boolean(readonly=True)

    upcoming_payments = fields.Monetary(readonly=True, currency_field='currency_id')
    upcoming_collections = fields.Monetary(readonly=True, currency_field='currency_id')

    def action_refresh(self):
        self.ensure_one()
        company = self.company_id
        today = fields.Date.context_today(self)
        display_currency = self.currency_id or company.currency_id

        def to_display(amount):
            return company.currency_id._convert(amount, display_currency, company, today)

        receivable_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
        ])
        payable_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.account_type', '=', 'liability_payable'),
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
        ])
        total_receivable = sum(receivable_lines.mapped('amount_residual'))
        total_payable = -sum(payable_lines.mapped('amount_residual'))

        overdue = receivable_lines.filtered(lambda l: (l.date_maturity or l.date) < today and l.amount_residual)
        upcoming_collections = sum(
            receivable_lines.filtered(lambda l: (l.date_maturity or l.date) >= today).mapped('amount_residual'))
        upcoming_payments = -sum(
            payable_lines.filtered(lambda l: (l.date_maturity or l.date) >= today).mapped('amount_residual'))

        bank_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.account_type', '=', 'asset_cash'),
            ('journal_id.type', '=', 'bank'),
            ('move_id.state', '=', 'posted'),
        ])
        cash_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.account_type', '=', 'asset_cash'),
            ('journal_id.type', '=', 'cash'),
            ('move_id.state', '=', 'posted'),
        ])
        unreconciled_count = self.env['account.bank.statement.line'].search_count([
            ('journal_id.company_id', '=', company.id), ('is_reconciled', '=', False),
        ])

        income_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.account_type', 'in', INCOME_TYPES),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
        ])
        expense_lines = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('account_id.account_type', 'in', EXPENSE_TYPES),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.date_from), ('date', '<=', self.date_to),
        ])
        monthly_revenue = -sum(income_lines.mapped('balance'))
        monthly_expense = sum(expense_lines.mapped('balance'))

        vals = {
            'currency_id': display_currency.id,
            'total_receivable': to_display(total_receivable),
            'total_payable': to_display(total_payable),
            'overdue_invoice_count': len(overdue.move_id),
            'overdue_invoice_amount': to_display(sum(overdue.mapped('amount_residual'))),
            'bank_balance': to_display(sum(bank_lines.mapped('balance'))),
            'cash_balance': to_display(sum(cash_lines.mapped('balance'))),
            'unreconciled_count': unreconciled_count,
            'monthly_revenue': to_display(monthly_revenue),
            'monthly_expense': to_display(monthly_expense),
            'monthly_profit': to_display(monthly_revenue - monthly_expense),
            'upcoming_payments': to_display(upcoming_payments),
            'upcoming_collections': to_display(upcoming_collections),
        }

        if 'gstr3b.report.wizard' in self.env:
            vals['gst_module_installed'] = True
            g3b = self.env['gstr3b.report.wizard'].create({
                'company_id': company.id, 'date_from': self.date_from, 'date_to': self.date_to,
            })
            g3b.action_generate()
            vals['gst_output_tax'] = to_display(g3b.total_tax_payable)
            vals['gst_input_credit'] = to_display(g3b.total_itc_available)
            vals['gst_net_payable'] = to_display(g3b.net_tax_payable)
        else:
            vals['gst_module_installed'] = False

        if 'account.budget' in self.env:
            vals['budget_module_installed'] = True
            budgets = self.env['account.budget'].search([
                ('company_id', '=', company.id), ('state', '!=', 'draft'),
                ('date_from', '<=', self.date_to), ('date_to', '>=', self.date_from),
            ])
            vals['budget_total'] = to_display(sum(budgets.mapped('budgeted_amount')))
            vals['budget_actual'] = to_display(sum(budgets.mapped('actual_amount')))
            vals['budget_variance'] = to_display(sum(budgets.mapped('variance_amount')))
        else:
            vals['budget_module_installed'] = False

        self.write(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'accounting.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'inline',
        }
