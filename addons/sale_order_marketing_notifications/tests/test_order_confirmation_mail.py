from unittest.mock import patch

from odoo.addons.sale.tests.common import SaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestOrderConfirmationMail(SaleCommon):

    def test_confirm_without_context_sends_mail(self):
        order = self.empty_order
        order.order_line = [(0, 0, {
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })]
        with patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._send_order_confirmation_mail'
        ) as mocked_send:
            order.action_confirm()
        mocked_send.assert_called_once()

    def test_confirm_with_send_email_false_does_not_force_mail(self):
        order = self.empty_order
        order.order_line = [(0, 0, {
            'product_id': self.product.id,
            'product_uom_qty': 1,
        })]
        with patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._send_order_confirmation_mail'
        ) as mocked_send:
            order.with_context(send_email=False).action_confirm()
        mocked_send.assert_not_called()
