from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAssetSaleWizard(models.TransientModel):
    _name = 'account.asset.sale.wizard'
    _description = 'Sell Asset Wizard'

    asset_id = fields.Many2one('account.asset', required=True)
    currency_id = fields.Many2one(related='asset_id.currency_id')
    sale_date = fields.Date(required=True, default=fields.Date.context_today)
    sale_price = fields.Monetary(required=True, currency_field='currency_id')
    proceeds_account_id = fields.Many2one(
        'account.account', string='Proceeds Account (Bank/Debtors)', required=True,
        domain="[('account_type', 'in', ('asset_cash', 'asset_current', 'asset_receivable'))]")

    def action_confirm(self):
        self.ensure_one()
        asset = self.asset_id
        if asset.state not in ('running', 'draft'):
            raise UserError(_("Only a draft or running asset can be sold."))
        category = asset.category_id

        # Write off any remaining book value as a final depreciation charge first.
        asset._write_off_remaining(date=self.sale_date)
        book_value = asset.book_value  # should now be 0, kept for clarity
        gain_loss = self.sale_price - book_value

        # Book proceeds Dr, remove remaining asset book value Cr, balance any gain/loss.
        lines = [
            (0, 0, {
                'account_id': self.proceeds_account_id.id,
                'name': _('Sale proceeds - %s', asset.name),
                'debit': self.sale_price, 'credit': 0.0,
            }),
        ]
        if gain_loss > 0:
            gain_account = category.gain_account_id or category.expense_account_id
            lines.append((0, 0, {
                'account_id': gain_account.id,
                'name': _('Gain on sale - %s', asset.name),
                'debit': 0.0, 'credit': gain_loss,
            }))
        elif gain_loss < 0:
            loss_account = category.loss_account_id or category.expense_account_id
            lines.append((0, 0, {
                'account_id': loss_account.id,
                'name': _('Loss on sale - %s', asset.name),
                'debit': abs(gain_loss), 'credit': 0.0,
            }))
        if book_value:
            lines.append((0, 0, {
                'account_id': category.asset_account_id.id,
                'name': _('Book value removed - %s', asset.name),
                'debit': 0.0, 'credit': book_value,
            }))

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': category.journal_id.id,
            'company_id': asset.company_id.id,
            'date': self.sale_date,
            'ref': _('Sale - %s', asset.name),
            'line_ids': lines,
        })
        move.action_post()
        asset.write({'state': 'sold'})
        asset.message_post(body=_(
            "Asset sold on %(date)s for %(price)s (book value written off: %(book)s, gain/loss: %(gl)s). Entry: %(move)s",
            date=self.sale_date, price=self.sale_price, book=book_value, gl=gain_loss, move=move.name,
        ))
        return {'type': 'ir.actions.act_window_close'}
