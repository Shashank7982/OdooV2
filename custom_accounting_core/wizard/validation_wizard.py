from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountValidationWizard(models.TransientModel):
    _name = 'account.validation.wizard'
    _description = 'Validate Accounting Entries'

    move_ids = fields.Many2many('account.move', string='Journal Entries')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def action_validate(self):
        helper = self.env['account.validation.helper']
        for move in self.move_ids:
            helper.ensure_balanced_move(move)
            helper.check_period_lock(move.date, move.journal_id)
            helper.check_partner_active(move.partner_id)
            for line in move.line_ids:
                helper.check_account_active(line.account_id)
                for tax in line.tax_ids:
                    helper.check_tax_valid(tax, move.date)
        return {'type': 'ir.actions.act_window_close'}