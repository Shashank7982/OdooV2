from odoo import _, api, fields, models


def _tax_breakup_for_line(line):
    """ Self-contained CGST/SGST/IGST/CESS breakup for one invoice line, proportioned
    from the line's actual tax amount (price_total - price_subtotal) so it always sums
    correctly regardless of any discount already applied. """
    breakup = {'cgst': 0.0, 'sgst': 0.0, 'igst': 0.0, 'cess': 0.0, 'other': 0.0}
    total_tax_amount = line.price_total - line.price_subtotal
    taxes = line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t.amount_type == 'percent')
    total_rate = sum(abs(t.amount) for t in taxes)
    if not taxes or not total_tax_amount or not total_rate:
        return breakup
    for tax in taxes:
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


class Gstr3bReportWizard(models.TransientModel):
    _name = 'gstr3b.report.wizard'
    _description = 'GSTR-3B Preparation Report'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one(related='company_id.currency_id')

    outward_taxable_value = fields.Monetary(readonly=True, currency_field='currency_id')
    output_cgst = fields.Monetary(readonly=True, currency_field='currency_id')
    output_sgst = fields.Monetary(readonly=True, currency_field='currency_id')
    output_igst = fields.Monetary(readonly=True, currency_field='currency_id')
    output_cess = fields.Monetary(readonly=True, currency_field='currency_id')
    total_tax_payable = fields.Monetary(readonly=True, currency_field='currency_id')

    inward_taxable_value = fields.Monetary(readonly=True, currency_field='currency_id')
    input_cgst = fields.Monetary(readonly=True, currency_field='currency_id')
    input_sgst = fields.Monetary(readonly=True, currency_field='currency_id')
    input_igst = fields.Monetary(readonly=True, currency_field='currency_id')
    input_cess = fields.Monetary(readonly=True, currency_field='currency_id')
    total_itc_available = fields.Monetary(readonly=True, currency_field='currency_id')

    net_tax_payable = fields.Monetary(readonly=True, currency_field='currency_id')

    def _aggregate(self, move_types):
        moves = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', move_types),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ])
        totals = {'taxable': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'igst': 0.0, 'cess': 0.0}
        for move in moves:
            sign = -1 if move.move_type in ('out_refund', 'in_refund') else 1
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                breakup = _tax_breakup_for_line(line)
                totals['taxable'] += sign * line.price_subtotal
                totals['cgst'] += sign * breakup['cgst']
                totals['sgst'] += sign * breakup['sgst']
                totals['igst'] += sign * breakup['igst']
                totals['cess'] += sign * breakup['cess']
        return totals

    def action_generate(self):
        self.ensure_one()
        out_totals = self._aggregate(['out_invoice', 'out_refund'])
        in_totals = self._aggregate(['in_invoice', 'in_refund'])

        output_tax_total = out_totals['cgst'] + out_totals['sgst'] + out_totals['igst'] + out_totals['cess']
        itc_total = in_totals['cgst'] + in_totals['sgst'] + in_totals['igst'] + in_totals['cess']

        self.write({
            'outward_taxable_value': out_totals['taxable'],
            'output_cgst': out_totals['cgst'],
            'output_sgst': out_totals['sgst'],
            'output_igst': out_totals['igst'],
            'output_cess': out_totals['cess'],
            'total_tax_payable': output_tax_total,
            'inward_taxable_value': in_totals['taxable'],
            'input_cgst': in_totals['cgst'],
            'input_sgst': in_totals['sgst'],
            'input_igst': in_totals['igst'],
            'input_cess': in_totals['cess'],
            'total_itc_available': itc_total,
            'net_tax_payable': output_tax_total - itc_total,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gstr3b.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
