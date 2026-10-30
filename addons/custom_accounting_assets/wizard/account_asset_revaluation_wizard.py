from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAssetRevaluationWizard(models.TransientModel):
    _name = 'account.asset.revaluation.wizard'
    _description = 'Revalue Asset Wizard'

    asset_id = fields.Many2one('account.asset', required=True)
    currency_id = fields.Many2one(related='asset_id.currency_id')
    revaluation_date = fields.Date(required=True, default=fields.Date.context_today)
    new_value = fields.Monetary(string='New Book Value', required=True, currency_field='currency_id')

    def action_confirm(self):
        self.ensure_one()
        asset = self.asset_id
        category = asset.category_id
        if not category.revaluation_account_id:
            raise UserError(_(
                "Set a Revaluation Reserve Account on the asset category '%s' before revaluing assets in it.",
                category.name))

        old_book_value = asset.book_value
        delta = self.new_value - old_book_value
        if not delta:
            raise UserError(_("New value is the same as the current book value — nothing to revalue."))

        lines = [
            (0, 0, {
                'account_id': category.asset_account_id.id if delta > 0 else category.revaluation_account_id.id,
                'name': _('Revaluation - %s', asset.name),
                'debit': abs(delta), 'credit': 0.0,
            }),
            (0, 0, {
                'account_id': category.revaluation_account_id.id if delta > 0 else category.asset_account_id.id,
                'name': _('Revaluation - %s', asset.name),
                'debit': 0.0, 'credit': abs(delta),
            }),
        ]
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': category.journal_id.id,
            'company_id': asset.company_id.id,
            'date': self.revaluation_date,
            'ref': _('Revaluation - %s', asset.name),
            'line_ids': lines,
        })
        move.action_post()

        # New purchase_value keeps salvage_value constant while shifting the base so
        # that (new purchase_value - salvage_value - already-posted depreciation) == new_value.
        already_depreciated = asset.depreciated_value
        asset.write({'purchase_value': self.new_value + already_depreciated + asset.salvage_value})
        asset._regenerate_remaining_schedule(self.new_value, start_date=self.revaluation_date)

        asset.message_post(body=_(
            "Asset revalued on %(date)s: book value changed from %(old)s to %(new)s. Entry: %(move)s",
            date=self.revaluation_date, old=old_book_value, new=self.new_value, move=move.name,
        ))
        return {'type': 'ir.actions.act_window_close'}
