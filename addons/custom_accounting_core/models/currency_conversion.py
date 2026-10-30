"""Company currency changes.

Odoo stores operational monetary values in the company currency.  When the
company currency changes, values which have not been posted yet can safely be
translated.  Posted journal entries are deliberately left untouched because
changing them would invalidate the accounting audit trail.
"""

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        """Use INR when a new company does not explicitly choose a currency."""
        inr = self.env.ref('base.INR', raise_if_not_found=False)
        if inr:
            for vals in vals_list:
                vals.setdefault('currency_id', inr.id)
        return super().create(vals_list)

    def write(self, vals):
        new_currency = self.env['res.currency'].browse(vals.get('currency_id'))
        companies = self.filtered(
            lambda company: vals.get('currency_id')
            and company.currency_id.id != vals['currency_id']
        )
        if companies:
            for company in companies:
                company._convert_operational_amounts(new_currency)
        return super().write(vals)

    def _convert_amount(self, amount, old_currency, new_currency, date):
        self.ensure_one()
        if not amount or old_currency == new_currency:
            return amount
        return old_currency._convert(amount, new_currency, self, date)

    def _convert_operational_amounts(self, new_currency):
        """Translate supported, unposted business values for this company."""
        self.ensure_one()
        old_currency = self.currency_id
        if not old_currency or not new_currency or old_currency == new_currency:
            return
        conversion_date = fields.Date.context_today(self)

        def convert(value):
            return self._convert_amount(value, old_currency, new_currency, conversion_date)

        # Product prices are company-dependent for company-specific products.
        # Global products are converted only for the main company, otherwise a
        # change in one company would alter another company's catalogue.
        products = self.env['product.template'].sudo().with_company(self).search([
            '|', ('company_id', '=', self.id),
            '&', ('company_id', '=', False), ('id', '!=', False),
        ])
        if self != self.env.company or self.id != self.env['res.company']._get_main_company().id:
            products = products.filtered(lambda product: product.company_id == self)
        for product in products:
            product.with_company(self).write({
                'list_price': convert(product.list_price),
                'standard_price': convert(product.standard_price),
            })

        # Pricelists and fixed-price rules are operational prices, not posted
        # accounting records, so both the currency and amounts are translated.
        pricelists = self.env['product.pricelist'].sudo().search([
            ('currency_id', '=', old_currency.id),
            '|', ('company_id', '=', self.id),
            '&', ('company_id', '=', False), ('id', '!=', False),
        ])
        for pricelist in pricelists:
            if pricelist.company_id and pricelist.company_id != self:
                continue
            pricelist.write({'currency_id': new_currency.id})
            for item in pricelist.item_ids:
                if item.fixed_price:
                    item.write({'fixed_price': convert(item.fixed_price)})

        # Custom operational records are translated only before they are posted.
        expense_model = self.env['custom.expense.entry'].sudo()
        for expense in expense_model.search([
            ('company_id', '=', self.id), ('state', '!=', 'posted'),
        ]):
            expense.write({
                'currency_id': new_currency.id,
                'amount': convert(expense.amount),
                'transport_amount': convert(expense.transport_amount),
                'hotel_amount': convert(expense.hotel_amount),
                'meals_amount': convert(expense.meals_amount),
            })

        voucher_model = self.env['account.petty.cash.voucher'].sudo()
        for voucher in voucher_model.search([
            ('company_id', '=', self.id), ('state', '!=', 'posted'),
        ]):
            voucher.write({'amount': convert(voucher.amount)})

        recurring_model = self.env['account.recurring.entry'].sudo()
        for line in recurring_model.search([('company_id', '=', self.id)]).mapped('line_ids'):
            line.write({
                'debit': convert(line.debit),
                'credit': convert(line.credit),
            })

        # Draft/submitted/approved journal entries can still be translated.
        # Posted moves are intentionally excluded to protect the audit trail.
        move_model = self.env['account.move'].sudo().with_context(
            skip_accounting_workflow=True, check_move_validity=False,
        )
        moves = move_model.search([
            ('company_id', '=', self.id), ('state', '!=', 'posted'),
        ])
        for move in moves:
            for line in move.line_ids:
                line.with_context(check_move_validity=False).write({
                    'debit': convert(line.debit),
                    'credit': convert(line.credit),
                })

