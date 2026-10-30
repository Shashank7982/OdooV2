from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AffiliateWithdrawal(models.Model):
    _name = 'affiliate.withdrawal'
    _description = 'Affiliate Withdrawal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    affiliate_id = fields.Many2one(
        'sale.affiliate', string='Affiliate', required=True, ondelete='cascade',
    )
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    state = fields.Selection([
        ('draft', 'Requested'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)
    request_date = fields.Datetime(
        string='Request Date', default=fields.Datetime.now, required=True,
    )
    payment_date = fields.Datetime(string='Payment Date')
    notes = fields.Text(string='Notes')

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise UserError(_('Withdrawal amount must be positive.'))

    def action_approve(self):
        self.filtered(lambda w: w.state == 'draft').write({'state': 'approved'})

    def action_pay(self):
        for rec in self.filtered(lambda w: w.state == 'approved'):
            rec.write({
                'state': 'paid',
                'payment_date': fields.Datetime.now(),
            })

    def action_reject(self):
        self.filtered(lambda w: w.state in ('draft', 'approved')).write({'state': 'rejected'})
