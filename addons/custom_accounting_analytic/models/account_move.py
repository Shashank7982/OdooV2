from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        for move in self:
            missing = move.line_ids.filtered(
                lambda l: l.account_id.require_analytic_distribution
                and l.display_type not in ('line_section', 'line_note')
                and not l.analytic_distribution
            )
            if missing:
                raise UserError(_(
                    "Cannot post this entry: the following account(s) require an analytic "
                    "distribution but none was set: %(accounts)s",
                    accounts=', '.join(missing.account_id.mapped('display_name')),
                ))
        return super()._post(soft=soft)
