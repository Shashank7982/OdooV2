from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _gst_get_tax_breakup(self):
        """ Returns {'taxable': float, 'cgst': float, 'sgst': float, 'igst': float, 'cess': float, 'other': float}
        for this invoice line, bucketing each applied tax by name so it can be shown as
        separate GST columns on the printed invoice.

        Uses price_subtotal/price_total (already net of the line discount) as the source of
        truth and prorates the real total tax amount across taxes by their percentage rate,
        rather than recomputing taxes from price_unit (which would ignore the line discount
        and produce a mismatched total). """
        self.ensure_one()
        breakup = {'taxable': self.price_subtotal, 'cgst': 0.0, 'sgst': 0.0, 'igst': 0.0, 'cess': 0.0, 'other': 0.0}
        total_tax_amount = self.price_total - self.price_subtotal
        taxes = self.tax_ids.flatten_taxes_hierarchy()
        percent_taxes = taxes.filtered(lambda t: t.amount_type == 'percent')
        if not percent_taxes or not total_tax_amount:
            return breakup

        total_rate = sum(abs(t.amount) for t in percent_taxes)
        if not total_rate:
            return breakup

        for tax in percent_taxes:
            name = (tax.name or '').upper()
            share = total_tax_amount * (abs(tax.amount) / total_rate)
            if 'CESS' in name:
                breakup['cess'] += share
            elif 'CGST' in name:
                breakup['cgst'] += share
            elif 'SGST' in name or 'UTGST' in name:
                breakup['sgst'] += share
            elif 'IGST' in name:
                breakup['igst'] += share
            else:
                breakup['other'] += share
        return breakup

    def _gst_is_shipping_line(self):
        self.ensure_one()
        return bool(self.sale_line_ids and any(self.sale_line_ids.mapped('is_delivery')))
