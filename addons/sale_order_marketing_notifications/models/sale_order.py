from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Always send the order-confirmation email to the customer on confirm,
        not only when confirming through the "Send by Email" quotation wizard
        (which is the only path core `sale` auto-sends on). An explicit
        send_email=False in context (e.g. a quiet programmatic confirmation)
        is still respected."""
        order = self
        if 'send_email' not in self.env.context:
            order = self.with_context(send_email=True)
        return super(SaleOrder, order).action_confirm()
