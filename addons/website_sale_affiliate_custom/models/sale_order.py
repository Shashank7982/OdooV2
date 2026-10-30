from odoo import models, fields, api
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_update_order_line(self, product_id, quantity, order_line, **kwargs):
        """Apply affiliate discount when a product is added/updated in the cart."""
        order_line = super()._cart_update_order_line(product_id, quantity, order_line, **kwargs)

        if not order_line or not request:
            return order_line

        affiliate_id = request.session.get('sale_affiliate_id')
        if not affiliate_id:
            return order_line

        affiliate = self.env['sale.affiliate'].sudo().browse(affiliate_id).exists()
        if not affiliate or not affiliate.is_active:
            return order_line

        # Assign the affiliate to the sale order if not already set
        if not self.affiliate_id:
            self.sudo().write({'affiliate_id': affiliate.id})

        # Apply the affiliate discount on the order line
        discount_rate = affiliate.discount_rate or 0.0
        if order_line.discount < discount_rate:
            order_line.sudo().write({'discount': discount_rate})

        return order_line

    def _try_apply_code(self, code):
        """Override to treat affiliate keys as reusable discount codes.

        Affiliate keys must not go through the loyalty/coupon engine: a `loyalty.card`
        is single-use (its points get consumed on first redemption), which made a second
        customer reusing the same affiliate key fail with "This coupon has already been
        used". Affiliate keys are handled entirely here instead, so they stay reusable.
        """
        affiliate = self.env['sale.affiliate'].sudo().search([
            ('key', '=', code),
            ('is_active', '=', True),
        ], limit=1)
        if affiliate:
            if not self.affiliate_id:
                self.sudo().write({'affiliate_id': affiliate.id})
            discount_rate = affiliate.discount_rate or 0.0
            for line in self.order_line.filtered('product_id'):
                if line.discount < discount_rate:
                    line.sudo().write({'discount': discount_rate})
            return {}
        return super()._try_apply_code(code)

    def action_confirm(self):
        """Override to create affiliate commission on order confirmation."""
        res = super().action_confirm()
        for order in self:
            if order.affiliate_id and order.affiliate_id.is_active and order.state == 'sale':
                rate = order.affiliate_id.commission_rate
                mrp_untaxed = sum(
                    line.price_unit * line.product_uom_qty
                    for line in order.order_line.filtered('product_id')
                )
                commission_amount = mrp_untaxed * (rate / 100.0)
                if commission_amount > 0:
                    # Check if commission already exists for this order
                    existing = self.env['affiliate.commission'].search([
                        ('sale_order_id', '=', order.id),
                        ('affiliate_id', '=', order.affiliate_id.id),
                    ], limit=1)
                    if not existing:
                        self.env['affiliate.commission'].create({
                            'affiliate_id': order.affiliate_id.id,
                            'sale_order_id': order.id,
                            'amount': commission_amount,
                            'rate': rate,
                            'state': 'confirmed',
                        })
                    # Mark any related clicks as converted
                    clicks = self.env['affiliate.click'].search([
                        ('affiliate_id', '=', order.affiliate_id.id),
                        ('converted', '=', False),
                        ('sale_order_id', '=', False),
                    ], limit=1)
                    if clicks:
                        clicks.write({
                            'converted': True,
                            'sale_order_id': order.id,
                        })
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'order_id.affiliate_id')
    def _compute_discount(self):
        super()._compute_discount()
        for line in self:
            if line.order_id.affiliate_id and line.order_id.affiliate_id.is_active:
                discount_rate = line.order_id.affiliate_id.discount_rate or 0.0
                if line.discount < discount_rate:
                    line.discount = discount_rate


