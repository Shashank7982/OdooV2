from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountDeferredSchedule(models.Model):
    _name = 'account.deferred.schedule'
    _description = 'Deferred Revenue / Expense Schedule'
    _order = 'start_date desc, name'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    partner_id = fields.Many2one('res.partner')
    deferred_type = fields.Selection([
        ('revenue', 'Deferred Revenue'),
        ('expense', 'Deferred Expense'),
    ], required=True, default='revenue')

    journal_id = fields.Many2one('account.journal', required=True, domain="[('type', '=', 'general')]")
    source_account_id = fields.Many2one(
        'account.account', required=True,
        help="Unearned revenue liability account, or prepaid expense asset account.")
    target_account_id = fields.Many2one(
        'account.account', required=True,
        help="Income account (for revenue) or expense account (for expense) to recognize into.")

    total_amount = fields.Monetary(required=True, currency_field='currency_id')
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date(required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('terminated', 'Terminated Early'),
    ], default='draft')

    line_ids = fields.One2many('account.deferred.schedule.line', 'schedule_id', string='Recognition Schedule')
    recognized_amount = fields.Monetary(compute='_compute_amounts', currency_field='currency_id')
    remaining_amount = fields.Monetary(compute='_compute_amounts', currency_field='currency_id')

    @api.depends('line_ids.amount', 'line_ids.posted', 'total_amount')
    def _compute_amounts(self):
        for schedule in self:
            schedule.recognized_amount = sum(schedule.line_ids.filtered('posted').mapped('amount'))
            schedule.remaining_amount = schedule.total_amount - schedule.recognized_amount

    def action_generate_schedule(self):
        for schedule in self:
            if schedule.end_date <= schedule.start_date:
                raise UserError(_("End date must be after start date."))
            schedule.line_ids.filtered(lambda l: not l.posted).unlink()

            months = max(1, (schedule.end_date.year - schedule.start_date.year) * 12
                         + (schedule.end_date.month - schedule.start_date.month) + 1)
            monthly_amount = schedule.total_amount / months
            remaining = schedule.total_amount
            lines = []
            date = schedule.start_date
            for i in range(months):
                amount = monthly_amount if i < months - 1 else remaining
                remaining -= amount
                lines.append((0, 0, {'sequence': i + 1, 'date': date, 'amount': amount}))
                date = date + relativedelta(months=1)

            schedule.write({'line_ids': lines, 'state': 'running'})

    def action_reset_to_draft(self):
        self.line_ids.filtered(lambda l: not l.posted).unlink()
        self.write({'state': 'draft'})

    def action_terminate_early(self):
        for schedule in self:
            remaining = schedule.remaining_amount
            if remaining:
                today = fields.Date.context_today(self)
                new_line = schedule.line_ids.create({
                    'schedule_id': schedule.id,
                    'sequence': (max(schedule.line_ids.mapped('sequence')) + 1) if schedule.line_ids else 1,
                    'date': today,
                    'amount': remaining,
                })
                new_line._post_entry()
            schedule.line_ids.filtered(lambda l: not l.posted).unlink()
            schedule.state = 'terminated'

    def _cron_post_due_recognition(self):
        today = fields.Date.context_today(self)
        due_lines = self.env['account.deferred.schedule.line'].search([
            ('posted', '=', False),
            ('date', '<=', today),
            ('schedule_id.state', '=', 'running'),
        ])
        for line in due_lines:
            line._post_entry()
        for schedule in due_lines.schedule_id:
            if not schedule.line_ids.filtered(lambda l: not l.posted):
                schedule.state = 'done'


class AccountDeferredScheduleLine(models.Model):
    _name = 'account.deferred.schedule.line'
    _description = 'Deferred Recognition Line'
    _order = 'schedule_id, sequence'

    schedule_id = fields.Many2one('account.deferred.schedule', required=True, ondelete='cascade')
    sequence = fields.Integer(default=1)
    date = fields.Date(required=True)
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='schedule_id.currency_id')
    posted = fields.Boolean(default=False, copy=False)
    move_id = fields.Many2one('account.move', readonly=True, copy=False)

    def _post_entry(self):
        for line in self:
            if line.posted:
                continue
            schedule = line.schedule_id
            is_revenue = schedule.deferred_type == 'revenue'
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': schedule.journal_id.id,
                'company_id': schedule.company_id.id,
                'date': line.date,
                'ref': _('Deferred Recognition - %s', schedule.name),
                'line_ids': [
                    (0, 0, {
                        'account_id': schedule.source_account_id.id if is_revenue else schedule.target_account_id.id,
                        'name': _('Recognition - %s', schedule.name),
                        'debit': line.amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': schedule.target_account_id.id if is_revenue else schedule.source_account_id.id,
                        'name': _('Recognition - %s', schedule.name),
                        'debit': 0.0,
                        'credit': line.amount,
                    }),
                ],
            })
            move.action_post()
            line.write({'posted': True, 'move_id': move.id})
