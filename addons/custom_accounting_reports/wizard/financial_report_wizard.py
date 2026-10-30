import base64
import csv
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError

BALANCE_SHEET_TYPES = (
    'asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed',
    'liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current',
    'equity', 'equity_unaffected',
)
PROFIT_LOSS_TYPES = ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')
ASSET_TYPES = ('asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed')
LIABILITY_TYPES = ('liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current')
EQUITY_TYPES = ('equity', 'equity_unaffected')
INCOME_TYPES = ('income', 'income_other')
EXPENSE_TYPES = ('expense', 'expense_depreciation', 'expense_direct_cost')


class FinancialReportWizard(models.Model):
    _name = 'financial.report.wizard'
    _description = 'Financial Report (Trial Balance / P&L / Balance Sheet)'
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)

    @api.depends('report_type', 'date_from', 'date_to')
    def _compute_name(self):
        labels = dict(self._fields['report_type'].selection)
        for wizard in self:
            wizard.name = '%s (%s - %s)' % (
                labels.get(wizard.report_type, ''), wizard.date_from or '...', wizard.date_to or '...')

    report_type = fields.Selection([
        ('trial_balance', 'Trial Balance'),
        ('profit_loss', 'Profit and Loss'),
        ('balance_sheet', 'Balance Sheet'),
        ('general_ledger', 'General Ledger'),
        ('cash_flow', 'Cash Flow Statement'),
        ('journal_audit', 'Journal Audit'),
    ], required=True, default='trial_balance')

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        'res.company', string='Consolidate Companies',
        help="Optional: select more than one company to produce a consolidated report "
             "(one sectioned block per company). Leave empty to use Company only.")
    date_from = fields.Date(default=lambda self: fields.Date.context_today(self).replace(day=1, month=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    journal_ids = fields.Many2many('account.journal', string='Journals (optional filter)')
    account_ids = fields.Many2many('account.account', string='Accounts (optional filter)')
    partner_ids = fields.Many2many('res.partner', string='Partners (optional filter)')
    analytic_account_ids = fields.Many2many('account.analytic.account', string='Analytic Accounts (optional filter)')
    currency_id = fields.Many2one(related='company_id.currency_id')

    line_ids = fields.One2many('financial.report.wizard.line', 'wizard_id', string='Report Lines')
    total_debit = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_credit = fields.Monetary(compute='_compute_totals', currency_field='currency_id')
    total_balance = fields.Monetary(compute='_compute_totals', currency_field='currency_id')

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.balance')
    def _compute_totals(self):
        for wizard in self:
            top_lines = wizard.line_ids.filtered(lambda l: not l.is_subtotal)
            wizard.total_debit = sum(top_lines.mapped('debit'))
            wizard.total_credit = sum(top_lines.mapped('credit'))
            wizard.total_balance = sum(top_lines.mapped('balance'))

    def _get_domain(self, account_types=None, date_from=None, company=None):
        domain = [
            ('move_id.company_id', '=', (company or self.company_id).id),
            ('move_id.state', '=', 'posted'),
            ('date', '<=', self.date_to),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if account_types:
            domain.append(('account_id.account_type', 'in', account_types))
        return domain

    def _matches_analytic_filter(self, line):
        if not self.analytic_account_ids:
            return True
        distribution = line.analytic_distribution or {}
        return any(str(account.id) in distribution for account in self.analytic_account_ids)

    def _filtered_move_lines(self, domain, order=None):
        lines = self.env['account.move.line'].search(domain, order=order)
        return lines.filtered(self._matches_analytic_filter)

    def _report_companies(self):
        return self.company_ids if len(self.company_ids) > 1 else self.company_id

    def _build_account_lines(self, account_types, date_from, section_label=None, company=None):
        """ Returns list of dict {account, debit, credit, balance} for accounts with movement. """
        domain = self._get_domain(account_types, date_from, company=company)
        if self.analytic_account_ids:
            grouped = {}
            for line in self._filtered_move_lines(domain):
                values = grouped.setdefault(line.account_id.id, {'debit': 0.0, 'credit': 0.0, 'balance': 0.0})
                values['debit'] += line.debit
                values['credit'] += line.credit
                values['balance'] += line.balance
            lines = [{'account_id': (account_id, self.env['account.account'].browse(account_id).display_name), **values}
                     for account_id, values in grouped.items()]
        else:
            lines = self.env['account.move.line'].read_group(domain, ['debit:sum', 'credit:sum', 'balance:sum'], ['account_id'])
        result = []
        for line in lines:
            if not line['account_id']:
                continue
            account = self.env['account.account'].browse(line['account_id'][0])
            result.append({
                'account_id': account.id,
                'debit': line['debit'],
                'credit': line['credit'],
                'balance': line['balance'],
            })
        return result

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        companies = self._report_companies()
        multi = len(companies) > 1
        vals_list = []
        for company in companies:
            if multi:
                vals_list.append({'wizard_id': self.id, 'label': _('=== %s ===', company.name), 'is_subtotal': True})
            vals_list += self._generate_lines_for_company(company)

        self.env['financial.report.wizard.line'].create(vals_list)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'financial.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _generate_lines_for_company(self, company):
        vals_list = []

        if self.report_type == 'trial_balance':
            for entry in self._build_account_lines(None, self.date_from, company=company):
                vals_list.append(dict(entry, wizard_id=self.id, is_subtotal=False))

        elif self.report_type == 'profit_loss':
            income = self._build_account_lines(INCOME_TYPES, self.date_from, company=company)
            expense = self._build_account_lines(EXPENSE_TYPES, self.date_from, company=company)
            vals_list.append({'wizard_id': self.id, 'label': _('INCOME'), 'is_subtotal': True})
            for entry in income:
                vals_list.append(dict(entry, wizard_id=self.id, is_subtotal=False))
            vals_list.append({
                'wizard_id': self.id, 'label': _('Total Income'), 'is_subtotal': True,
                'balance': -sum(e['balance'] for e in income),
            })
            vals_list.append({'wizard_id': self.id, 'label': _('EXPENSES'), 'is_subtotal': True})
            for entry in expense:
                vals_list.append(dict(entry, wizard_id=self.id, is_subtotal=False))
            vals_list.append({
                'wizard_id': self.id, 'label': _('Total Expenses'), 'is_subtotal': True,
                'balance': sum(e['balance'] for e in expense),
            })
            net = -sum(e['balance'] for e in income) - sum(e['balance'] for e in expense)
            vals_list.append({'wizard_id': self.id, 'label': _('NET PROFIT / (LOSS)'), 'is_subtotal': True, 'balance': net})

        elif self.report_type == 'balance_sheet':
            assets = self._build_account_lines(ASSET_TYPES, None, company=company)
            liabilities = self._build_account_lines(LIABILITY_TYPES, None, company=company)
            equity = self._build_account_lines(EQUITY_TYPES, None, company=company)
            pl_income = self._build_account_lines(INCOME_TYPES, None, company=company)
            pl_expense = self._build_account_lines(EXPENSE_TYPES, None, company=company)
            retained_earnings = -sum(e['balance'] for e in pl_income) - sum(e['balance'] for e in pl_expense)

            vals_list.append({'wizard_id': self.id, 'label': _('ASSETS'), 'is_subtotal': True})
            for entry in assets:
                vals_list.append(dict(entry, wizard_id=self.id, is_subtotal=False))
            total_assets = sum(e['balance'] for e in assets)
            vals_list.append({'wizard_id': self.id, 'label': _('Total Assets'), 'is_subtotal': True, 'balance': total_assets})

            vals_list.append({'wizard_id': self.id, 'label': _('LIABILITIES'), 'is_subtotal': True})
            for entry in liabilities:
                vals_list.append(dict(entry, wizard_id=self.id, is_subtotal=False))
            total_liabilities = -sum(e['balance'] for e in liabilities)
            vals_list.append({'wizard_id': self.id, 'label': _('Total Liabilities'), 'is_subtotal': True, 'balance': total_liabilities})

            vals_list.append({'wizard_id': self.id, 'label': _('EQUITY'), 'is_subtotal': True})
            for entry in equity:
                vals_list.append(dict(entry, wizard_id=self.id, is_subtotal=False))
            total_equity = -sum(e['balance'] for e in equity) + retained_earnings
            vals_list.append({'wizard_id': self.id, 'label': _('Retained Earnings (Current P&L)'), 'is_subtotal': True, 'balance': retained_earnings})
            vals_list.append({'wizard_id': self.id, 'label': _('Total Equity'), 'is_subtotal': True, 'balance': total_equity})
            vals_list.append({
                'wizard_id': self.id, 'label': _('Total Liabilities + Equity'), 'is_subtotal': True,
                'balance': total_liabilities + total_equity,
            })

        elif self.report_type == 'general_ledger':
            domain = self._get_domain(None, self.date_from, company=company)
            move_lines = self._filtered_move_lines(domain, order='account_id, date, id')
            current_account = None
            running_balance = 0.0
            for ml in move_lines:
                if ml.account_id != current_account:
                    current_account = ml.account_id
                    running_balance = 0.0
                    vals_list.append({
                        'wizard_id': self.id, 'label': current_account.display_name, 'is_subtotal': True,
                    })
                running_balance += ml.debit - ml.credit
                vals_list.append({
                    'wizard_id': self.id, 'is_subtotal': False,
                    'account_id': ml.account_id.id, 'move_id': ml.move_id.id,
                    'partner_id': ml.partner_id.id, 'entry_date': ml.date,
                    'debit': ml.debit, 'credit': ml.credit, 'balance': ml.balance,
                    'running_balance': running_balance,
                })

        elif self.report_type == 'cash_flow':
            buckets = [('operating', _('Operating Activities')), ('investing', _('Investing Activities')), ('financing', _('Financing Activities'))]
            net_total = 0.0
            for key, label in buckets:
                domain = self._get_domain(None, self.date_from, company=company)
                domain.append(('account_id.cash_flow_category', '=', key))
                if self.analytic_account_ids:
                    bucket_total = -sum(self._filtered_move_lines(domain).mapped('balance'))
                else:
                    lines = self.env['account.move.line'].read_group(domain, ['balance:sum'], [])
                    bucket_total = -(lines[0]['balance'] if lines else 0.0)
                vals_list.append({'wizard_id': self.id, 'label': label, 'is_subtotal': True, 'balance': bucket_total})
                net_total += bucket_total
            vals_list.append({'wizard_id': self.id, 'label': _('Net Increase in Cash'), 'is_subtotal': True, 'balance': net_total})

        elif self.report_type == 'journal_audit':
            journals = self.journal_ids or self.env['account.journal'].search([('company_id', '=', company.id)])
            for journal in journals:
                domain = self._get_domain(None, self.date_from, company=company)
                domain.append(('journal_id', '=', journal.id))
                move_lines = self._filtered_move_lines(domain, order='date, move_id, id')
                if not move_lines:
                    continue
                vals_list.append({'wizard_id': self.id, 'label': journal.name, 'is_subtotal': True})
                running_balance = 0.0
                for ml in move_lines:
                    running_balance += ml.debit - ml.credit
                    vals_list.append({
                        'wizard_id': self.id, 'is_subtotal': False,
                        'account_id': ml.account_id.id, 'move_id': ml.move_id.id,
                        'partner_id': ml.partner_id.id, 'entry_date': ml.date,
                        'debit': ml.debit, 'credit': ml.credit, 'balance': ml.balance,
                        'running_balance': running_balance,
                    })

        return vals_list

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('custom_accounting_reports.action_report_financial_report').report_action(self)

    def action_export_csv(self):
        self.ensure_one()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Label/Account', 'Date', 'Partner', 'Debit', 'Credit', 'Balance', 'Running Balance'])
        for line in self.line_ids:
            writer.writerow([
                line.account_id.display_name if line.account_id else line.label,
                line.entry_date or '',
                line.partner_id.display_name or '',
                line.debit, line.credit, line.balance, line.running_balance,
            ])
        content = buffer.getvalue().encode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': 'financial_report_%s.csv' % self.report_type,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'mimetype': 'text/csv',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_export_xlsx(self):
        self.ensure_one()
        try:
            from openpyxl import Workbook
        except ImportError as error:
            raise UserError(_('openpyxl is required for XLSX export.')) from error
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Financial Report'
        sheet.append(['Label/Account', 'Date', 'Partner', 'Debit', 'Credit', 'Balance', 'Running Balance'])
        for line in self.line_ids:
            sheet.append([
                line.account_id.display_name if line.account_id else line.label,
                str(line.entry_date or ''), line.partner_id.display_name or '',
                line.debit, line.credit, line.balance, line.running_balance,
            ])
        output = io.BytesIO()
        workbook.save(output)
        attachment = self.env['ir.attachment'].create({
            'name': 'financial_report_%s.xlsx' % self.report_type,
            'type': 'binary', 'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name, 'res_id': self.id,
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%s?download=true' % attachment.id, 'target': 'self'}


class FinancialReportWizardLine(models.Model):
    _name = 'financial.report.wizard.line'
    _description = 'Financial Report Wizard Line'
    _order = 'id'

    wizard_id = fields.Many2one('financial.report.wizard', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account')
    move_id = fields.Many2one('account.move')
    partner_id = fields.Many2one('res.partner')
    entry_date = fields.Date()
    running_balance = fields.Monetary(currency_field='currency_id')
    label = fields.Char()
    is_subtotal = fields.Boolean(default=False)
    debit = fields.Monetary(currency_field='currency_id')
    credit = fields.Monetary(currency_field='currency_id')
    balance = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    def action_view_journal_items(self):
        self.ensure_one()
        wizard = self.wizard_id
        domain = wizard._get_domain(None, wizard.date_from if wizard.report_type != 'balance_sheet' else None)
        domain.append(('account_id', '=', self.account_id.id))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items'),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
        }
