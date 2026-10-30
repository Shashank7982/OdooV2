from odoo import _, api, fields, models

INCOME_TYPES = ('income', 'income_other')
COGS_TYPES = ('expense_direct_cost',)
OPEX_TYPES = ('expense', 'expense_depreciation')

GROUP_BY_OPTIONS = [
    ('none', 'Total Only'),
    ('customer', 'Customer'),
    ('product', 'Product'),
    ('salesperson', 'Salesperson'),
    ('analytic', 'Department / Analytic Account'),
    ('company', 'Company'),
    ('date', 'Date Range (Monthly)'),
]


class ProfitabilityReportWizard(models.TransientModel):
    _name = 'profitability.report.wizard'
    _description = 'Profitability Analysis'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        'res.company', string='Consolidate Companies',
        help="Optional: select more than one company to consolidate. Leave empty to use Company only.")
    date_from = fields.Date(default=lambda self: fields.Date.context_today(self).replace(day=1, month=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    group_by = fields.Selection(GROUP_BY_OPTIONS, string='Breakdown By', default='none', required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')

    total_revenue = fields.Monetary(readonly=True, currency_field='currency_id')
    total_cogs = fields.Monetary(string='Cost of Goods Sold', readonly=True, currency_field='currency_id')
    total_opex = fields.Monetary(string='Operating Expenses', readonly=True, currency_field='currency_id')
    gross_profit = fields.Monetary(readonly=True, currency_field='currency_id')
    net_profit = fields.Monetary(readonly=True, currency_field='currency_id')
    profit_margin = fields.Float(string='Profit Margin (%)', readonly=True)

    line_ids = fields.One2many('profitability.report.wizard.line', 'wizard_id', string='Breakdown')

    def _report_companies(self):
        return self.company_ids if len(self.company_ids) > 1 else self.company_id

    def _group_key(self, line):
        move = line.move_id
        if self.group_by == 'customer':
            return move.partner_id.display_name or _('No Partner')
        if self.group_by == 'product':
            return line.product_id.display_name or _('No Product')
        if self.group_by == 'salesperson':
            salesperson = move.invoice_user_id or move.user_id
            return salesperson.name or _('No Salesperson')
        if self.group_by == 'company':
            return move.company_id.display_name
        if self.group_by == 'date':
            return line.date.strftime('%Y-%m') if line.date else _('No Date')
        return _('Total')

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        companies = self._report_companies()

        domain = [
            ('move_id.company_id', 'in', companies.ids),
            ('move_id.state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('account_id.account_type', 'in', INCOME_TYPES + COGS_TYPES + OPEX_TYPES),
        ]
        lines = self.env['account.move.line'].search(domain)

        totals = {'revenue': 0.0, 'cogs': 0.0, 'opex': 0.0}
        agg = {}

        for line in lines:
            account_type = line.account_id.account_type
            is_revenue = account_type in INCOME_TYPES
            is_cogs = account_type in COGS_TYPES
            amount = -line.balance if is_revenue else line.balance
            bucket_field = 'revenue' if is_revenue else ('cogs' if is_cogs else 'opex')
            totals[bucket_field] += amount

            if self.group_by == 'analytic':
                if not line.analytic_distribution:
                    continue
                for analytic_id_str, percentage in line.analytic_distribution.items():
                    analytic = self.env['account.analytic.account'].browse(int(analytic_id_str))
                    key = analytic.display_name
                    bucket = agg.setdefault(key, {
                        'revenue': 0.0, 'cogs': 0.0, 'opex': 0.0,
                        'analytic_account_id': analytic.id,
                    })
                    bucket[bucket_field] += amount * (percentage / 100.0)
            else:
                key = self._group_key(line)
                bucket = agg.setdefault(key, {'revenue': 0.0, 'cogs': 0.0, 'opex': 0.0})
                bucket[bucket_field] += amount

        self.env['profitability.report.wizard.line'].create([
            {
                'wizard_id': self.id,
                'group_label': key,
                'analytic_account_id': vals.get('analytic_account_id'),
                'revenue': vals['revenue'],
                'cogs': vals['cogs'],
                'opex': vals['opex'],
            }
            for key, vals in sorted(agg.items())
        ])

        gross_profit = totals['revenue'] - totals['cogs']
        net_profit = gross_profit - totals['opex']
        self.write({
            'total_revenue': totals['revenue'],
            'total_cogs': totals['cogs'],
            'total_opex': totals['opex'],
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'profit_margin': (net_profit / totals['revenue']) if totals['revenue'] else 0.0,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'profitability.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class ProfitabilityReportWizardLine(models.TransientModel):
    _name = 'profitability.report.wizard.line'
    _description = 'Profitability Report Line'
    _order = 'group_label'

    wizard_id = fields.Many2one('profitability.report.wizard', required=True, ondelete='cascade')
    group_label = fields.Char(string='Breakdown')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    revenue = fields.Monetary(currency_field='currency_id')
    cogs = fields.Monetary(string='COGS', currency_field='currency_id')
    opex = fields.Monetary(string='Operating Expenses', currency_field='currency_id')
    gross_profit = fields.Monetary(compute='_compute_profit', currency_field='currency_id')
    net_profit = fields.Monetary(compute='_compute_profit', currency_field='currency_id')
    margin = fields.Float(string='Margin (%)', compute='_compute_profit')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.depends('revenue', 'cogs', 'opex')
    def _compute_profit(self):
        for line in self:
            line.gross_profit = line.revenue - line.cogs
            line.net_profit = line.gross_profit - line.opex
            line.margin = (line.net_profit / line.revenue) if line.revenue else 0.0
