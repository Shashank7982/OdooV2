from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountingClose(models.Model):
    _name = 'custom.accounting.close'
    _description = 'Accounting Period Close'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, tracking=True)
    close_type = fields.Selection([('month', 'Month End'), ('year', 'Year End')], required=True, default='month', tracking=True)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'), ('review', 'Checks Complete'), ('approved', 'Controller Approved'), ('locked', 'Locked'),
    ], default='draft', required=True, tracking=True)
    sales_reviewed = fields.Boolean(string='Sales Reviewed')
    purchase_reviewed = fields.Boolean(string='Purchases Reviewed')
    bank_reconciled = fields.Boolean(string='Bank Reconciled')
    asset_deferred_reviewed = fields.Boolean(string='Assets and Deferred Reviewed')
    reports_reviewed = fields.Boolean(string='Reports Reviewed')
    controller_approved = fields.Boolean(string='Controller Approval')
    exception_count = fields.Integer(readonly=True)
    exception_summary = fields.Text(readonly=True)
    retained_earnings_account_id = fields.Many2one(
        'account.account', string='Retained Earnings Account', check_company=True,
        domain="[('company_ids', 'in', company_id), ('account_type', 'in', ('equity', 'equity_unaffected'))]",
    )
    journal_id = fields.Many2one(
        'account.journal', string='Closing Journal', check_company=True,
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
    )
    closing_move_id = fields.Many2one('account.move', readonly=True, copy=False)
    attachment_ids = fields.Many2many('ir.attachment', string='Close Package')
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.accounting.close') or 'New'
        return super().create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for close in self:
            if close.date_from > close.date_to:
                raise ValidationError(_('Close start date must be on or before the end date.'))

    def action_run_checks(self):
        for close in self:
            company = close.company_id
            exceptions = []
            draft_count = self.env['account.move'].search_count([
                ('company_id', '=', company.id), ('date', '>=', close.date_from),
                ('date', '<=', close.date_to), ('state', '=', 'draft'),
            ])
            if draft_count:
                exceptions.append(_('%s draft journal entries remain in the period.') % draft_count)
            unreconciled = self.env['account.move.line'].search_count([
                ('company_id', '=', company.id), ('date', '<=', close.date_to),
                ('account_id.account_type', '=', 'asset_cash'), ('full_reconcile_id', '=', False),
                ('move_id.state', '=', 'posted'),
            ])
            if unreconciled:
                exceptions.append(_('%s cash/bank journal items are not fully reconciled.') % unreconciled)
            due_assets = self.env['account.asset.depreciation.line'].search_count([
                ('asset_id.company_id', '=', company.id), ('date', '<=', close.date_to), ('posted', '=', False),
            ])
            if due_assets:
                exceptions.append(_('%s depreciation lines are due but not posted.') % due_assets)
            due_deferred = self.env['account.deferred.schedule.line'].search_count([
                ('schedule_id.company_id', '=', company.id), ('date', '<=', close.date_to), ('posted', '=', False),
            ])
            if due_deferred:
                exceptions.append(_('%s deferred recognition lines are due but not posted.') % due_deferred)
            close.write({
                'exception_count': len(exceptions),
                'exception_summary': '\n'.join(exceptions) or _('No automated exceptions found.'),
                'state': 'review',
            })

    def action_approve(self):
        for close in self:
            if close.state != 'review':
                raise UserError(_('Run the close checks before approval.'))
            checklist = [
                close.sales_reviewed, close.purchase_reviewed, close.bank_reconciled,
                close.asset_deferred_reviewed, close.reports_reviewed, close.controller_approved,
            ]
            if not all(checklist):
                raise ValidationError(_('Complete every close checklist item before approval.'))
            close.state = 'approved'

    def action_generate_closing_entry(self):
        for close in self:
            if close.state not in ('approved', 'locked'):
                raise UserError(_('Approve the close before generating the closing entry.'))
            if close.closing_move_id:
                continue
            if not close.retained_earnings_account_id or not close.journal_id:
                raise ValidationError(_('Select a retained earnings account and a general closing journal.'))
            lines = self.env['account.move.line'].search([
                ('company_id', '=', close.company_id.id), ('date', '>=', close.date_from),
                ('date', '<=', close.date_to), ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')),
            ])
            balances = {}
            for line in lines:
                balances.setdefault(line.account_id.id, 0.0)
                balances[line.account_id.id] += line.debit - line.credit
            move_lines = []
            net = 0.0
            for account_id, balance in balances.items():
                if not balance:
                    continue
                amount = abs(balance)
                net += balance
                move_lines.append((0, 0, {
                    'account_id': account_id,
                    'name': _('Year/period close - %s', close.name),
                    'debit': amount if balance < 0 else 0.0,
                    'credit': amount if balance > 0 else 0.0,
                }))
            if not move_lines:
                raise UserError(_('There is no income or expense balance to close for this period.'))
            move_lines.append((0, 0, {
                'account_id': close.retained_earnings_account_id.id,
                'name': _('Retained earnings - %s', close.name),
                'debit': net if net > 0 else 0.0,
                'credit': abs(net) if net < 0 else 0.0,
            }))
            move = self.env['account.move'].create({
                'move_type': 'entry', 'company_id': close.company_id.id, 'journal_id': close.journal_id.id,
                'date': close.date_to, 'ref': close.name,
                'source_model': close._name, 'source_res_id': close.id,
                'source_event_key': 'period_close:%s' % close.id,
                'line_ids': move_lines,
            })
            move.action_post()
            close.closing_move_id = move.id

    def action_lock(self):
        for close in self:
            if close.state != 'approved':
                raise UserError(_('Only an approved close can be locked.'))
            close.company_id.write({'fiscalyear_lock_date': close.date_to})
            close.state = 'locked'

    def action_view_closing_move(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': self.closing_move_id.id, 'view_mode': 'form'}
