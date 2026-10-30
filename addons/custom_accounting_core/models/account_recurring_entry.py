from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountRecurringEntry(models.Model):
    _name = 'account.recurring.entry'
    _description = 'Recurring Journal Entry Template'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', required=True, domain="[('company_id', '=', company_id)]")
    currency_id = fields.Many2one(related='company_id.currency_id')
    ref = fields.Char(string='Reference')

    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], required=True, default='monthly')
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    next_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date(help="Leave empty to repeat indefinitely.")

    line_ids = fields.One2many('account.recurring.entry.line', 'recurring_entry_id', string='Template Lines')
    generated_move_ids = fields.One2many('account.move', 'recurring_entry_id', string='Generated Entries')
    generated_move_count = fields.Integer(compute='_compute_generated_move_count')

    total_debit = fields.Monetary(compute='_compute_totals')
    total_credit = fields.Monetary(compute='_compute_totals')
    is_balanced = fields.Boolean(compute='_compute_totals')

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for record in self:
            record.total_debit = sum(record.line_ids.mapped('debit'))
            record.total_credit = sum(record.line_ids.mapped('credit'))
            record.is_balanced = record.currency_id.compare_amounts(record.total_debit, record.total_credit) == 0

    def _compute_generated_move_count(self):
        for record in self:
            record.generated_move_count = len(record.generated_move_ids)

    def action_generate_now(self):
        for record in self:
            record._generate_move()

    def action_view_generated_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('recurring_entry_id', '=', self.id)],
        }

    def _generate_move(self):
        self.ensure_one()
        if not self.is_balanced:
            raise UserError(_(
                "Cannot generate entry for '%(name)s': template is not balanced (Debit %(debit)s != Credit %(credit)s).",
                name=self.name, debit=self.total_debit, credit=self.total_credit,
            ))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date': self.next_date,
            'ref': self.ref or self.name,
            'recurring_entry_id': self.id,
            'line_ids': [(0, 0, {
                'account_id': line.account_id.id,
                'name': line.name,
                'partner_id': line.partner_id.id,
                'debit': line.debit,
                'credit': line.credit,
            }) for line in self.line_ids],
        })
        self._advance_next_date()
        return move

    def _advance_next_date(self):
        self.ensure_one()
        step = {'monthly': relativedelta(months=1), 'quarterly': relativedelta(months=3), 'yearly': relativedelta(years=1)}
        self.next_date = self.next_date + step[self.frequency]
        if self.end_date and self.next_date > self.end_date:
            self.active = False

    def _cron_generate_recurring_entries(self):
        today = fields.Date.context_today(self)
        due = self.search([
            ('active', '=', True),
            ('next_date', '<=', today),
            ('line_ids', '!=', False),
        ])
        for record in due:
            if record.is_balanced:
                record._generate_move()


class AccountRecurringEntryLine(models.Model):
    _name = 'account.recurring.entry.line'
    _description = 'Recurring Journal Entry Template Line'

    recurring_entry_id = fields.Many2one('account.recurring.entry', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', required=True)
    partner_id = fields.Many2one('res.partner')
    name = fields.Char(string='Label')
    debit = fields.Monetary(default=0.0, currency_field='currency_id')
    credit = fields.Monetary(default=0.0, currency_field='currency_id')
    currency_id = fields.Many2one(related='recurring_entry_id.currency_id')

    @api.constrains('debit', 'credit')
    def _check_debit_credit(self):
        for line in self:
            if line.debit and line.credit:
                raise ValidationError(_("A journal item line cannot have both a debit and a credit amount."))
            if not line.debit and not line.credit:
                raise ValidationError(_(
                    "Line '%s' has no debit or credit amount - remove it or enter an amount.", line.name or line.account_id.display_name))
