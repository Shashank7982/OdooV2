from odoo import _, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_id = fields.Many2one('account.asset', string='Generated Asset', readonly=True, copy=False)

    def action_create_asset(self):
        self.ensure_one()
        asset = self.env['account.asset'].create({
            'name': self.name or self.product_id.name or _('Asset from %s', self.move_id.name),
            'company_id': self.move_id.company_id.id,
            'partner_id': self.move_id.partner_id.id,
            'purchase_date': self.move_id.invoice_date or fields.Date.context_today(self),
            'purchase_value': abs(self.price_subtotal),
            'vendor_bill_line_id': self.id,
            'category_id': self.env['account.asset.category'].search(
                [('company_id', '=', self.move_id.company_id.id)], limit=1).id,
        })
        self.asset_id = asset.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'form',
            'res_id': asset.id,
        }
