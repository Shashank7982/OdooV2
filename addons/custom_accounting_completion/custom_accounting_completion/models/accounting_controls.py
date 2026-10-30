from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    """One shared posting boundary for the custom accounting suite.

    Odoo remains the posting authority: this layer validates the inputs and
    records provenance, then delegates posting to the normal account.move
    implementation and any installed localisation modules.
    """

    _inherit = 'account.move'

    source_model = fields.Char(string='Source Model', copy=False, index=True, readonly=True)
    source_res_id = fields.Integer(string='Source Record ID', copy=False, readonly=True)
    source_user_id = fields.Many2one('res.users', string='Source User', copy=False, readonly=True)
    source_event_key = fields.Char(string='Idempotency Key', copy=False, index=True, readonly=True)

    _sql_constraints = [
        ('source_event_key_company_uniq', 'unique(company_id, source_event_key)',
         'The accounting source event has already generated a journal entry.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('source_model') or vals.get('source_event_key')) and not vals.get('source_user_id'):
                vals['source_user_id'] = self.env.uid
        return super().create(vals_list)

    def _validate_plan_posting_boundary(self):
        for move in self:
            if move.journal_id and move.journal_id.company_id != move.company_id:
                raise ValidationError(_('Journal and journal entry must belong to the same company.'))
            if not move.date:
                raise ValidationError(_('A journal entry date is required.'))
            for line in move.line_ids:
                if line.account_id and line.account_id.deprecated:
                    raise ValidationError(_('Deprecated account %s cannot be used for a new entry.') % line.account_id.display_name)
                if line.account_id and move.company_id not in line.account_id.company_ids:
                    raise ValidationError(_('Account %s is not configured for this company.') % line.account_id.display_name)
                if line.debit and line.credit:
                    raise ValidationError(_('A journal item cannot contain both debit and credit.'))
            if move.is_invoice(include_receipts=True) and move.partner_id and not move.partner_id.active:
                raise ValidationError(_('An inactive customer or vendor cannot be posted on an invoice.'))
        return True

    def _post(self, soft=True):
        self._validate_plan_posting_boundary()
        return super()._post(soft=soft)


class AccountRecurringEntry(models.Model):
    _inherit = 'account.recurring.entry'

    def _generate_move(self):
        self.ensure_one()
        event_key = 'recurring:%s:%s' % (self.id, self.next_date)
        existing = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('source_event_key', '=', event_key),
        ], limit=1)
        if existing:
            self._advance_next_date()
            return existing
        move = super()._generate_move()
        move.write({
            'source_model': self._name,
            'source_res_id': self.id,
            'source_event_key': event_key,
        })
        return move


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    def _post_entry(self):
        for line in self:
            if line.posted:
                continue
            event_key = 'asset_depreciation:%s' % line.id
            existing = self.env['account.move'].search([
                ('company_id', '=', line.asset_id.company_id.id),
                ('source_event_key', '=', event_key),
            ], limit=1)
            if existing:
                line.write({'posted': True, 'move_id': existing.id})
                continue
            super(AccountAssetDepreciationLine, line)._post_entry()
            if line.move_id:
                line.move_id.write({
                    'source_model': line._name,
                    'source_res_id': line.id,
                    'source_event_key': event_key,
                })


class AccountDeferredScheduleLine(models.Model):
    _inherit = 'account.deferred.schedule.line'

    def _post_entry(self):
        for line in self:
            if line.posted:
                continue
            event_key = 'deferred_recognition:%s' % line.id
            existing = self.env['account.move'].search([
                ('company_id', '=', line.schedule_id.company_id.id),
                ('source_event_key', '=', event_key),
            ], limit=1)
            if existing:
                line.write({'posted': True, 'move_id': existing.id})
                continue
            super(AccountDeferredScheduleLine, line)._post_entry()
            if line.move_id:
                line.move_id.write({
                    'source_model': line._name,
                    'source_res_id': line.id,
                    'source_event_key': event_key,
                })
