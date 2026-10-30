from odoo import _, api, fields, models

from .gstr3b_report_wizard import _tax_breakup_for_line


def _gstr1_tax_split(move):
    """ CGST/SGST/IGST/CESS split for one invoice, reusing the same
    per-line breakup logic as the GSTR-3B report so both stay consistent. """
    totals = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}
    for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
        breakup = _tax_breakup_for_line(line)
        totals['igst'] += breakup['igst']
        totals['cgst'] += breakup['cgst']
        totals['sgst'] += breakup['sgst']
        totals['cess'] += breakup['cess']
    return totals


class Gstr1ReportWizard(models.TransientModel):
    _name = 'gstr1.report.wizard'
    _description = 'GSTR-1 Preparation Report'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)

    b2b_line_ids = fields.One2many('gstr1.report.wizard.line', 'wizard_id', domain=[('line_type', '=', 'b2b')], string='B2B Invoices')
    b2c_line_ids = fields.One2many('gstr1.report.wizard.line', 'wizard_id', domain=[('line_type', '=', 'b2c')], string='B2C Invoices')
    hsn_line_ids = fields.One2many('gstr1.report.hsn.line', 'wizard_id', string='HSN Summary')

    total_b2b_taxable = fields.Monetary(compute='_compute_totals')
    total_b2c_taxable = fields.Monetary(compute='_compute_totals')
    total_tax = fields.Monetary(compute='_compute_totals')
    currency_id = fields.Many2one(related='company_id.currency_id')

    @api.depends('b2b_line_ids.taxable_value', 'b2c_line_ids.taxable_value', 'b2b_line_ids.tax_amount', 'b2c_line_ids.tax_amount')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_b2b_taxable = sum(wizard.b2b_line_ids.mapped('taxable_value'))
            wizard.total_b2c_taxable = sum(wizard.b2c_line_ids.mapped('taxable_value'))
            wizard.total_tax = sum(wizard.b2b_line_ids.mapped('tax_amount')) + sum(wizard.b2c_line_ids.mapped('tax_amount'))

    def action_generate(self):
        self.ensure_one()
        self.b2b_line_ids.unlink()
        self.b2c_line_ids.unlink()
        self.hsn_line_ids.unlink()

        moves = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ])

        b2b_vals, b2c_vals = [], []
        hsn_agg = {}

        for move in moves:
            sign = -1 if move.move_type == 'out_refund' else 1
            is_b2b = bool(move.partner_id.vat)
            tax_split = _gstr1_tax_split(move)
            line_vals = {
                'move_id': move.id,
                'invoice_number': move.name,
                'invoice_date': move.invoice_date,
                'partner_name': move.partner_id.name,
                'partner_gstin': move.partner_id.vat or '',
                'taxable_value': sign * move.amount_untaxed,
                'igst_amount': sign * tax_split['igst'],
                'cgst_amount': sign * tax_split['cgst'],
                'sgst_amount': sign * tax_split['sgst'],
                'cess_amount': sign * tax_split['cess'],
                'tax_amount': sign * move.amount_tax,
                'total_value': sign * move.amount_total,
                'source': move.journal_id.name,
            }
            (b2b_vals if is_b2b else b2c_vals).append(line_vals)

            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                hsn = line.product_id.l10n_in_hsn_code or _('(no HSN)')
                bucket = hsn_agg.setdefault(hsn, {'qty': 0.0, 'taxable': 0.0, 'tax': 0.0})
                bucket['qty'] += sign * line.quantity
                bucket['taxable'] += sign * line.price_subtotal
                bucket['tax'] += sign * (line.price_total - line.price_subtotal)

        self.env['gstr1.report.wizard.line'].create([
            dict(v, wizard_id=self.id, line_type='b2b') for v in b2b_vals
        ] + [
            dict(v, wizard_id=self.id, line_type='b2c') for v in b2c_vals
        ])
        self.env['gstr1.report.hsn.line'].create([
            {'wizard_id': self.id, 'hsn_code': hsn, 'quantity': vals['qty'], 'taxable_value': vals['taxable'], 'tax_amount': vals['tax']}
            for hsn, vals in hsn_agg.items()
        ])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gstr1.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class Gstr1ReportWizardLine(models.TransientModel):
    _name = 'gstr1.report.wizard.line'
    _description = 'GSTR-1 Invoice Line'

    wizard_id = fields.Many2one('gstr1.report.wizard', required=True, ondelete='cascade')
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    line_type = fields.Selection([('b2b', 'B2B'), ('b2c', 'B2C')], required=True)
    invoice_number = fields.Char()
    invoice_date = fields.Date()
    partner_name = fields.Char()
    partner_gstin = fields.Char()
    taxable_value = fields.Monetary(string='Total Taxable Value', currency_field='currency_id')
    igst_amount = fields.Monetary(string='Integrated Tax', currency_field='currency_id')
    cgst_amount = fields.Monetary(string='Central Tax', currency_field='currency_id')
    sgst_amount = fields.Monetary(string='State/UT Tax', currency_field='currency_id')
    cess_amount = fields.Monetary(string='Cess', currency_field='currency_id')
    tax_amount = fields.Monetary(currency_field='currency_id')
    total_value = fields.Monetary(string='Total Invoice Value', currency_field='currency_id')
    source = fields.Char(string='Source')
    currency_id = fields.Many2one(related='wizard_id.currency_id')

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class Gstr1ReportHsnLine(models.TransientModel):
    _name = 'gstr1.report.hsn.line'
    _description = 'GSTR-1 HSN Summary Line'

    wizard_id = fields.Many2one('gstr1.report.wizard', required=True, ondelete='cascade')
    hsn_code = fields.Char()
    quantity = fields.Float()
    taxable_value = fields.Monetary(currency_field='currency_id')
    tax_amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id')
