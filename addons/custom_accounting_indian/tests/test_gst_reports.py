from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestGstReports(AccountTestInvoicingCommon):

    def test_gstr1_empty_period_returns_zero(self):
        wizard = self.env['gstr1.report.wizard'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2020-01-01',
            'date_to': '2020-01-31',
        })
        wizard.action_generate()
        self.assertEqual(wizard.total_b2b_taxable, 0.0)
        self.assertEqual(wizard.total_tax, 0.0)
        self.assertFalse(wizard.b2b_line_ids)

    def test_gstr3b_empty_period_returns_zero(self):
        wizard = self.env['gstr3b.report.wizard'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2020-01-01',
            'date_to': '2020-01-31',
        })
        wizard.action_generate()
        self.assertEqual(wizard.net_tax_payable, 0.0)

    def test_gstr1_and_gstr3b_aggregate_taxed_invoice(self):
        self.partner_a.vat = '27AAAAA0000A1Z5'
        cgst = self.env['account.tax'].create({
            'name': 'CGST 9%', 'amount': 9.0, 'amount_type': 'percent', 'type_tax_use': 'sale',
            'company_id': self.company_data['company'].id,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id}),
            ],
        })
        sgst = self.env['account.tax'].create({
            'name': 'SGST 9%', 'amount': 9.0, 'amount_type': 'percent', 'type_tax_use': 'sale',
            'company_id': self.company_data['company'].id,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id}),
            ],
        })
        product = self.env['product.product'].create({
            'name': 'GST Report Product', 'list_price': 1000.0,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'company_id': self.company_data['company'].id,
            'invoice_date': '2026-05-10',
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id, 'name': 'Consulting',
                'quantity': 1,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, (cgst + sgst).ids)],
            })],
        })
        invoice.action_post()

        gstr1 = self.env['gstr1.report.wizard'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2026-05-01', 'date_to': '2026-05-31',
        })
        gstr1.action_generate()
        self.assertEqual(round(gstr1.total_b2b_taxable, 2), 1000.0)
        self.assertEqual(round(gstr1.total_tax, 2), 180.0)

        gstr3b = self.env['gstr3b.report.wizard'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2026-05-01', 'date_to': '2026-05-31',
        })
        gstr3b.action_generate()
        self.assertEqual(round(gstr3b.output_cgst, 2), 90.0)
        self.assertEqual(round(gstr3b.output_sgst, 2), 90.0)
        self.assertEqual(round(gstr3b.total_tax_payable, 2), 180.0)
