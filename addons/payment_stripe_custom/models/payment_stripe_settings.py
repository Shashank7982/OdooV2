from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stripe_publishable_key = fields.Char(string='Stripe Publishable Key')
    stripe_secret_key = fields.Char(string='Stripe Secret Key')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        res.update(
            stripe_publishable_key=IrConfig.get_param('payment_stripe.publishable_key', default=''),
            stripe_secret_key=IrConfig.get_param('payment_stripe.secret_key', default=''),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        IrConfig.set_param('payment_stripe.publishable_key', self.stripe_publishable_key or '')
        IrConfig.set_param('payment_stripe.secret_key', self.stripe_secret_key or '')
