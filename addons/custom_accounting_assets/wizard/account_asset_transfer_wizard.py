from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountAssetTransferWizard(models.TransientModel):
    _name = 'account.asset.transfer.wizard'
    _description = 'Transfer Asset Wizard'

    asset_id = fields.Many2one('account.asset', required=True)
    company_id = fields.Many2one('res.company', string='New Company', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='New Analytic Account')
    note = fields.Char(string='Reason / Note')

    def action_confirm(self):
        self.ensure_one()
        asset = self.asset_id
        if self.company_id != asset.company_id:
            raise UserError(_(
                "Cross-company asset transfer is not supported: it requires posting matching "
                "entries in two separate companies, which is out of scope for this module. "
                "Only the same-company analytic/ownership reassignment below is supported."))

        old_analytic = asset.analytic_account_id
        asset.write({'analytic_account_id': self.analytic_account_id.id})
        asset.message_post(body=_(
            "Asset transferred: analytic account changed from %(old)s to %(new)s. %(note)s",
            old=old_analytic.display_name or _('None'),
            new=self.analytic_account_id.display_name or _('None'),
            note=self.note or '',
        ))
        return {'type': 'ir.actions.act_window_close'}
