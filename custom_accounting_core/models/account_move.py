from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    source_model = fields.Char('Source Model', readonly=True, copy=False)
    source_id = fields.Integer('Source ID', readonly=True, copy=False)
    audit_action = fields.Selection([
        ('create', 'Created'),
        ('reverse', 'Reversed'),
        ('adjust', 'Adjusted'),
    ], string='Audit Action', readonly=True, copy=False)
    audit_user_id = fields.Many2one('res.users', 'Audit User', readonly=True, copy=False)
    audit_timestamp = fields.Datetime('Audit Timestamp', readonly=True, copy=False)
    reversal_move_id = fields.Many2one('account.move', 'Reversal Entry', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.state == 'draft':
                move._validate_on_create()
        return moves

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'posted':
            for move in self:
                move._validate_before_post()
        return super().write(vals)

    def _validate_on_create(self):
        self.ensure_one()
        helper = self.env['account.validation.helper']
        helper.check_company(self)
        helper.check_period_lock(self.date, self.journal_id)
        helper.check_partner_active(self.partner_id)
        for line in self.line_ids:
            helper.check_account_active(line.account_id)
            if line.tax_ids:
                for tax in line.tax_ids:
                    helper.check_tax_valid(tax, self.date)

    def _validate_before_post(self):
        self.ensure_one()
        helper = self.env['account.validation.helper']
        helper.ensure_balanced_move(self)
        helper.check_period_lock(self.date, self.journal_id)
        # Additional validations: duplicate vendor bill, analytic, etc.
        if self.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            if helper.check_duplicate_vendor_bill(self.partner_id, self.ref, self.journal_id, self.date):
                raise ValidationError(_("Duplicate vendor bill detected for this partner/reference/date."))
        if self.company_id.account_analytic_required and not any(line.analytic_distribution for line in self.line_ids):
            helper.check_analytic_distribution(False, required=True)

    def _post(self, soft=True):
        # Override to add audit metadata if missing
        for move in self:
            if not move.source_model:
                move.write({
                    'source_model': 'account.move',
                    'source_id': move.id,
                    'audit_action': 'create',
                    'audit_user_id': self.env.user.id,
                    'audit_timestamp': fields.Datetime.now(),
                })
        return super()._post(soft)

    def action_reverse(self, **kwargs):
        """Override reversal to link reversal entry and set audit action."""
        res = super().action_reverse(**kwargs)
        if res.get('res_id'):
            reversal = self.env['account.move'].browse(res['res_id'])
            reversal.write({
                'reversal_move_id': self.id,
                'audit_action': 'reverse',
                'audit_user_id': self.env.user.id,
                'audit_timestamp': fields.Datetime.now(),
            })
        return res