from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    affiliate_default_commission_rate = fields.Float(
        string='Default Commission Rate (%)',
        config_parameter='website_sale_affiliate_custom.default_commission_rate',
        default=10.0,
    )
    affiliate_auto_approve_withdrawals = fields.Boolean(
        string='Auto-Approve Withdrawals',
        config_parameter='website_sale_affiliate_custom.auto_approve_withdrawals',
        default=False,
    )
    affiliate_min_withdrawal_amount = fields.Float(
        string='Minimum Withdrawal Amount',
        config_parameter='website_sale_affiliate_custom.min_withdrawal_amount',
        default=50.0,
    )
