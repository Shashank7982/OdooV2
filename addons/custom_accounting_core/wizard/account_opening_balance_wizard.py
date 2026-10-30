from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountOpeningBalanceWizard(models.TransientModel):
    _name = 'account.opening.balance.wizard'
    _description = 'Opening Balance Wizard'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one(
        'account.journal', required=True, domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
        help="A miscellaneous/general journal to post the opening balance entry into.")
    date = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('account.opening.balance.wizard.line', 'wizard_id', string='Opening Balances')
    currency_id = fields.Many2one(related='company_id.currency_id')

    total_debit = fields.Monetary(compute='_compute_totals')
    total_credit = fields.Monetary(compute='_compute_totals')
    is_balanced = fields.Boolean(compute='_compute_totals')

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_debit = sum(wizard.line_ids.mapped('debit'))
            wizard.total_credit = sum(wizard.line_ids.mapped('credit'))
            wizard.is_balanced = wizard.currency_id.compare_amounts(wizard.total_debit, wizard.total_credit) == 0

    def action_create_opening_entry(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Add at least one account balance line."))
        if not self.is_balanced:
            raise UserError(_(
                "Opening balance is not balanced: Debit %(debit)s != Credit %(credit)s.",
                debit=self.total_debit, credit=self.total_credit,
            ))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'ref': _('Opening Balance'),
            'line_ids': [(0, 0, {
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'name': _('Opening Balance'),
                'debit': line.debit,
                'credit': line.credit,
            }) for line in self.line_ids],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }


class AccountOpeningBalanceWizardLine(models.TransientModel):
    _name = 'account.opening.balance.wizard.line'
    _description = 'Opening Balance Wizard Line'

    wizard_id = fields.Many2one('account.opening.balance.wizard', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', required=True)
    partner_id = fields.Many2one('res.partner')
    debit = fields.Monetary(default=0.0, currency_field='currency_id')
    credit = fields.Monetary(default=0.0, currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    @api.constrains('debit', 'credit')
    def _check_debit_credit(self):
        for line in self:
            if line.debit and line.credit:
                raise ValidationError(_("A journal item line cannot have both a debit and a credit amount."))
            if not line.debit and not line.credit:
                raise ValidationError(_(
                    "Line for '%s' has no debit or credit amount - remove it or enter an amount.", line.account_id.display_name))
