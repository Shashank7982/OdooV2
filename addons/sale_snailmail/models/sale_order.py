# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _snailmail_check_address(self):
        self.ensure_one()
        if not self.env['snailmail.letter']._is_valid_address(self.partner_id):
            raise UserError(_(
                "%s's address is incomplete. Street, city, zip and country are "
                "required to send this order by post.", self.partner_id.name,
            ))

    def _snailmail_create_letter(self, user=None):
        """Create and immediately send a snailmail.letter for this order,
        printing it with the standard Quotation/Order report. Shared by the
        backend button and the portal route so both go through the same
        checks."""
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            raise UserError(_("Only confirmed sales orders can be sent by post."))
        self._snailmail_check_address()
        letter = self.env['snailmail.letter'].sudo().create({
            'model': 'sale.order',
            'res_id': self.id,
            'partner_id': self.partner_id.id,
            'user_id': (user or self.env.user).id,
            'report_template': self.env.ref('sale.action_report_saleorder').id,
        })
        letter.snailmail_print()
        return letter

    def action_send_by_post(self):
        self.ensure_one()
        self._snailmail_create_letter()
        return True
