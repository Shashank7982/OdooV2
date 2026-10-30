from odoo import fields, models


class AccountingDashboard(models.TransientModel):
    _inherit = 'accounting.dashboard'

    affiliate_module_installed = fields.Boolean(readonly=True)
    affiliate_total_commission = fields.Monetary(readonly=True, currency_field='currency_id')
    affiliate_paid_commission = fields.Monetary(readonly=True, currency_field='currency_id')
    affiliate_pending_commission = fields.Monetary(readonly=True, currency_field='currency_id')
    affiliate_count = fields.Integer(readonly=True)

    def action_refresh(self):
        result = super().action_refresh()
        self.ensure_one()
        affiliates = self.env['sale.affiliate'].search([('is_active', '=', True)])
        company = self.company_id
        display_currency = self.currency_id or company.currency_id
        today = fields.Date.context_today(self)

        def to_display(amount):
            return company.currency_id._convert(amount, display_currency, company, today)

        self.write({
            'affiliate_module_installed': True,
            'affiliate_count': len(affiliates),
            'affiliate_total_commission': to_display(sum(affiliates.mapped('total_commission'))),
            'affiliate_paid_commission': to_display(sum(affiliates.mapped('paid_commission'))),
            'affiliate_pending_commission': to_display(sum(affiliates.mapped('pending_commission'))),
        })
        return result
