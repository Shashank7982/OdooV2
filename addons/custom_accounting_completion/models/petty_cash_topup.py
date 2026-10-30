from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PettyCashTopup(models.Model):
    _name = 'account.petty.cash.topup'
    _description = 'Petty Cash Top-up / Replenishment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False, tracking=True)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    location_id = fields.Many2one('account.cash.location', required=True, check_company=True, tracking=True)
    company_id = fields.Many2one(related='location_id.company_id', store=True, readonly=True)
    cash_journal_id = fields.Many2one(related='location_id.journal_id', store=True, readonly=True)
    funding_journal_id = fields.Many2one(
        'account.journal', required=True, string='Funding Journal', check_company=True,
        domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]",
    )
    amount = fields.Monetary(required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    reference = fields.Char(required=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('posted', 'Posted'), ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)
    move_id = fields.Many2one('account.move', readonly=True, copy=False)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.petty.cash.topup') or 'New'
        return super().create(vals_list)

    @api.constrains('amount', 'funding_journal_id', 'location_id')
    def _check_values(self):
        for topup in self:
            if topup.amount <= 0:
                raise ValidationError(_('Petty-cash top-up amount must be greater than zero.'))
            if topup.funding_journal_id and topup.funding_journal_id.company_id != topup.company_id:
                raise ValidationError(_('Funding journal must belong to the same company.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        for topup in self:
            if topup.state != 'submitted':
                raise UserError(_('Only a submitted top-up can be approved.'))
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_post(self):
        for topup in self:
            if topup.state != 'approved':
                raise UserError(_('Approve the top-up before posting it.'))
            if topup.move_id:
                continue
            cash_account = topup.cash_journal_id.default_account_id
            funding_account = topup.funding_journal_id.default_account_id
            if not cash_account or not funding_account:
                raise ValidationError(_('Configure default accounts on both the cash and funding journals.'))
            move = self.env['account.move'].create({
                'move_type': 'entry', 'company_id': topup.company_id.id, 'journal_id': topup.funding_journal_id.id,
                'date': topup.date, 'ref': topup.reference,
                'source_model': topup._name, 'source_res_id': topup.id,
                'source_event_key': 'petty_cash_topup:%s' % topup.id,
                'transaction_mode': 'cash', 'cash_journal_id': topup.cash_journal_id.id,
                'cash_location_id': topup.location_id.id, 'cash_payment_method': 'cash',
                'cash_receipt_ref': topup.reference,
                'line_ids': [(0, 0, {
                    'account_id': cash_account.id, 'name': topup.reference, 'debit': topup.amount, 'credit': 0.0,
                }), (0, 0, {
                    'account_id': funding_account.id, 'name': topup.reference, 'debit': 0.0, 'credit': topup.amount,
                })],
            })
            move.action_post()
            topup.write({'move_id': move.id, 'state': 'posted'})

    def action_view_move(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'account.move', 'res_id': self.move_id.id, 'view_mode': 'form'}
