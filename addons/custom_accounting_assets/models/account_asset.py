from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAsset(models.Model):
    _name = 'account.asset'
    _description = 'Fixed Asset'
    _order = 'purchase_date desc, name'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, tracking=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    category_id = fields.Many2one('account.asset.category', required=True)
    asset_type = fields.Selection(related='category_id.asset_type', store=True, string='Asset Type')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', tracking=True)
    vendor_bill_line_id = fields.Many2one('account.move.line', string='Source Vendor Bill Line', readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor')

    purchase_date = fields.Date(required=True, default=fields.Date.context_today)
    purchase_value = fields.Monetary(required=True, currency_field='currency_id')
    salvage_value = fields.Monetary(default=0.0, currency_field='currency_id')

    method = fields.Selection(related='category_id.method', readonly=True)
    duration_months = fields.Integer(related='category_id.duration_months', readonly=False)
    declining_rate = fields.Float(related='category_id.declining_rate', readonly=False)

    # Shown read-only on the asset form so the category's accounting setup is
    # visible without navigating to Asset Categories separately.
    category_journal_id = fields.Many2one(related='category_id.journal_id', string='Journal', readonly=True)
    category_asset_account_id = fields.Many2one(related='category_id.asset_account_id', string='Fixed Asset Account', readonly=True)
    category_depreciation_account_id = fields.Many2one(related='category_id.depreciation_account_id', string='Accumulated Depreciation Account', readonly=True)
    category_expense_account_id = fields.Many2one(related='category_id.expense_account_id', string='Depreciation Expense Account', readonly=True)
    category_gain_account_id = fields.Many2one(related='category_id.gain_account_id', string='Gain on Sale Account', readonly=True)
    category_loss_account_id = fields.Many2one(related='category_id.loss_account_id', string='Loss on Sale Account', readonly=True)
    category_revaluation_account_id = fields.Many2one(related='category_id.revaluation_account_id', string='Revaluation Reserve Account', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('disposed', 'Disposed'),
        ('sold', 'Sold'),
    ], default='draft', tracking=True)

    depreciation_line_ids = fields.One2many('account.asset.depreciation.line', 'asset_id', string='Depreciation Schedule')
    depreciated_value = fields.Monetary(compute='_compute_depreciated_value', currency_field='currency_id', store=True)
    book_value = fields.Monetary(compute='_compute_depreciated_value', currency_field='currency_id', store=True)

    @api.depends('depreciation_line_ids.amount', 'depreciation_line_ids.posted', 'purchase_value')
    def _compute_depreciated_value(self):
        for asset in self:
            asset.depreciated_value = sum(asset.depreciation_line_ids.filtered('posted').mapped('amount'))
            asset.book_value = asset.purchase_value - asset.depreciated_value

    def action_generate_schedule(self):
        for asset in self:
            asset.depreciation_line_ids.filtered(lambda l: not l.posted).unlink()
            depreciable_base = asset.purchase_value - asset.salvage_value
            if depreciable_base <= 0:
                raise UserError(_("Purchase value must be greater than salvage value."))

            lines = []
            date = asset.purchase_date
            if asset.method == 'linear':
                months = asset.duration_months or 1
                monthly_amount = depreciable_base / months
                remaining = depreciable_base
                for i in range(months):
                    date = date + relativedelta(months=1)
                    amount = monthly_amount if i < months - 1 else remaining
                    remaining -= amount
                    lines.append((0, 0, {'sequence': i + 1, 'date': date, 'amount': amount}))
            else:  # declining
                remaining_book = depreciable_base
                monthly_rate = (asset.declining_rate / 100.0) / 12.0
                i = 0
                # cap iterations to avoid runaway loops; stop once remaining book value is negligible
                while remaining_book > 0.01 and i < 600:
                    i += 1
                    date = date + relativedelta(months=1)
                    amount = min(remaining_book, remaining_book * monthly_rate) or remaining_book
                    remaining_book -= amount
                    lines.append((0, 0, {'sequence': i, 'date': date, 'amount': amount}))

            asset.write({'depreciation_line_ids': lines, 'state': 'running'})

    def _regenerate_remaining_schedule(self, new_base, start_date=None):
        """Replace unposted depreciation lines with a fresh schedule computed on `new_base`,
        starting from `start_date` (or today), preserving already-posted history."""
        self.ensure_one()
        self.depreciation_line_ids.filtered(lambda l: not l.posted).unlink()
        if new_base <= 0:
            return
        date = start_date or fields.Date.context_today(self)
        next_seq = (max(self.depreciation_line_ids.mapped('sequence')) + 1) if self.depreciation_line_ids else 1
        lines = []
        if self.method == 'linear':
            months = self.duration_months or 1
            monthly_amount = new_base / months
            remaining = new_base
            for i in range(months):
                date = date + relativedelta(months=1)
                amount = monthly_amount if i < months - 1 else remaining
                remaining -= amount
                lines.append((0, 0, {'sequence': next_seq + i, 'date': date, 'amount': amount}))
        else:
            remaining_book = new_base
            monthly_rate = (self.declining_rate / 100.0) / 12.0
            i = 0
            while remaining_book > 0.01 and i < 600:
                i += 1
                date = date + relativedelta(months=1)
                amount = min(remaining_book, remaining_book * monthly_rate) or remaining_book
                remaining_book -= amount
                lines.append((0, 0, {'sequence': next_seq + i - 1, 'date': date, 'amount': amount}))
        self.write({'depreciation_line_ids': lines})

    def action_reset_to_draft(self):
        self.depreciation_line_ids.filtered(lambda l: not l.posted).unlink()
        self.write({'state': 'draft'})

    def _write_off_remaining(self, date=None):
        """Post a final depreciation line for any remaining book value. Returns the amount written off."""
        self.ensure_one()
        remaining = self.book_value
        if remaining:
            self.depreciation_line_ids.create({
                'asset_id': self.id,
                'sequence': (max(self.depreciation_line_ids.mapped('sequence')) + 1) if self.depreciation_line_ids else 1,
                'date': date or fields.Date.context_today(self),
                'amount': remaining,
            })._post_entry()
        return remaining

    def action_dispose(self):
        for asset in self:
            asset._write_off_remaining()
            asset.state = 'disposed'

    def action_sell(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset.sale.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id, 'default_sale_price': self.book_value},
        }

    def action_transfer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_company_id': self.company_id.id,
                'default_analytic_account_id': self.analytic_account_id.id,
            },
        }

    def action_revalue(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset.revaluation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id, 'default_new_value': self.book_value},
        }

    def _cron_post_due_depreciation(self):
        today = fields.Date.context_today(self)
        due_lines = self.env['account.asset.depreciation.line'].search([
            ('posted', '=', False),
            ('date', '<=', today),
            ('asset_id.state', '=', 'running'),
        ])
        for line in due_lines:
            line._post_entry()


class AccountAssetDepreciationLine(models.Model):
    _name = 'account.asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'asset_id, sequence'

    asset_id = fields.Many2one('account.asset', required=True, ondelete='cascade')
    sequence = fields.Integer(default=1)
    date = fields.Date(required=True)
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='asset_id.currency_id')
    posted = fields.Boolean(default=False, copy=False)
    move_id = fields.Many2one('account.move', readonly=True, copy=False)

    def _post_entry(self):
        for line in self:
            if line.posted:
                continue
            category = line.asset_id.category_id
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': category.journal_id.id,
                'company_id': line.asset_id.company_id.id,
                'date': line.date,
                'ref': _('Depreciation - %s', line.asset_id.name),
                'line_ids': [
                    (0, 0, {
                        'account_id': category.expense_account_id.id,
                        'name': _('Depreciation - %s', line.asset_id.name),
                        'debit': line.amount, 'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': category.depreciation_account_id.id,
                        'name': _('Depreciation - %s', line.asset_id.name),
                        'debit': 0.0, 'credit': line.amount,
                    }),
                ],
            })
            move.action_post()
            line.write({'posted': True, 'move_id': move.id})
