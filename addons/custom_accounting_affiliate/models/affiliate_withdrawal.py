from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AffiliateWithdrawal(models.Model):
    _inherit = 'affiliate.withdrawal'

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company, required=True,
    )
    journal_id = fields.Many2one(
        'account.journal', string='Payment Journal',
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal_id(),
        help='Bank/cash journal to pay this affiliate from.',
    )
    payment_id = fields.Many2one(
        'account.payment', string='Accounting Payment', readonly=True, copy=False,
    )
    payment_state = fields.Selection(related='payment_id.state', string='Payment Status')

    def _default_journal_id(self):
        return self.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash')), ('company_id', '=', self.env.company.id),
        ], limit=1)

    def action_pay(self):
        for rec in self.filtered(lambda w: w.state == 'approved'):
            if not rec.journal_id:
                raise UserError(_('Set a payment journal before marking "%s" as paid.') % rec.affiliate_id.name)
            if not rec.affiliate_id.partner_id:
                raise UserError(_('Affiliate "%s" has no linked partner to pay.') % rec.affiliate_id.name)

            payment = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': rec.affiliate_id.partner_id.id,
                'amount': rec.amount,
                'currency_id': rec.currency_id.id,
                'journal_id': rec.journal_id.id,
                'company_id': rec.company_id.id,
                'date': fields.Date.context_today(self),
                'memo': _('Affiliate Commission Payout - %s', rec.affiliate_id.name),
            })
            payment.action_post()

            rec.write({
                'state': 'paid',
                'payment_date': fields.Datetime.now(),
                'payment_id': payment.id,
            })

    def action_view_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
        }
