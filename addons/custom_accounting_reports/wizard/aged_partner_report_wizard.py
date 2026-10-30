from odoo import _, api, fields, models


class AgedPartnerReportWizard(models.Model):
    _name = 'aged.partner.report.wizard'
    _description = 'Aged Receivable / Aged Payable Report'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)

    @api.depends('report_type', 'as_of_date')
    def _compute_name(self):
        labels = dict(self._fields['report_type'].selection)
        for wizard in self:
            wizard.name = '%s (as of %s)' % (labels.get(wizard.report_type, ''), wizard.as_of_date or '...')

    report_type = fields.Selection([
        ('receivable', 'Aged Receivable'),
        ('payable', 'Aged Payable'),
    ], required=True, default='receivable')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    as_of_date = fields.Date(required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(related='company_id.currency_id')

    line_ids = fields.One2many('aged.partner.report.wizard.line', 'wizard_id', string='Report Lines')
    total_not_due = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_1_30 = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_31_60 = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_61_90 = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_90_plus = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_amount = fields.Monetary(compute='_compute_totals', currency_field='currency_id')

    @api.depends('line_ids.not_due', 'line_ids.due_1_30', 'line_ids.due_31_60', 'line_ids.due_61_90', 'line_ids.due_90_plus')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_not_due = sum(wizard.line_ids.mapped('not_due'))
            wizard.total_1_30 = sum(wizard.line_ids.mapped('due_1_30'))
            wizard.total_31_60 = sum(wizard.line_ids.mapped('due_31_60'))
            wizard.total_61_90 = sum(wizard.line_ids.mapped('due_61_90'))
            wizard.total_90_plus = sum(wizard.line_ids.mapped('due_90_plus'))
            wizard.total_amount = (
                wizard.total_not_due + wizard.total_1_30 + wizard.total_31_60
                + wizard.total_61_90 + wizard.total_90_plus
            )

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        account_type = 'asset_receivable' if self.report_type == 'receivable' else 'liability_payable'

        lines = self.env['account.move.line'].search([
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', '=', account_type),
            ('move_id.state', '=', 'posted'),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
        ])

        by_partner = {}
        for line in lines:
            residual = line.amount_residual if account_type == 'asset_receivable' else -line.amount_residual
            if line.currency_id and line.currency_id != line.company_currency_id:
                residual = line.amount_residual_currency if account_type == 'asset_receivable' else -line.amount_residual_currency
            if not residual:
                continue
            due_date = line.date_maturity or line.date
            days_overdue = (self.as_of_date - due_date).days
            bucket = by_partner.setdefault(line.partner_id.id, {
                'partner_id': line.partner_id.id,
                'not_due': 0.0, 'due_1_30': 0.0, 'due_31_60': 0.0, 'due_61_90': 0.0, 'due_90_plus': 0.0,
            })
            if days_overdue <= 0:
                bucket['not_due'] += residual
            elif days_overdue <= 30:
                bucket['due_1_30'] += residual
            elif days_overdue <= 60:
                bucket['due_31_60'] += residual
            elif days_overdue <= 90:
                bucket['due_61_90'] += residual
            else:
                bucket['due_90_plus'] += residual

        self.env['aged.partner.report.wizard.line'].create([
            dict(vals, wizard_id=self.id) for vals in by_partner.values()
        ])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'aged.partner.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class AgedPartnerReportWizardLine(models.Model):
    _name = 'aged.partner.report.wizard.line'
    _description = 'Aged Partner Report Line'

    wizard_id = fields.Many2one('aged.partner.report.wizard', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner')
    not_due = fields.Monetary(currency_field='currency_id')
    due_1_30 = fields.Monetary(currency_field='currency_id')
    due_31_60 = fields.Monetary(currency_field='currency_id')
    due_61_90 = fields.Monetary(currency_field='currency_id')
    due_90_plus = fields.Monetary(currency_field='currency_id')
    total = fields.Monetary(compute='_compute_total', currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.depends('not_due', 'due_1_30', 'due_31_60', 'due_61_90', 'due_90_plus')
    def _compute_total(self):
        for line in self:
            line.total = line.not_due + line.due_1_30 + line.due_31_60 + line.due_61_90 + line.due_90_plus
