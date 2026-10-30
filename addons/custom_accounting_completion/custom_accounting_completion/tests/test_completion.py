import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountingPlanCompletion(AccountTestInvoicingCommon):

    def test_posting_records_source_metadata(self):
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': self.company_data['default_journal_misc'].id,
            'company_id': self.company_data['company'].id, 'date': fields.Date.today(),
            'source_model': 'test.source', 'source_res_id': 99, 'source_event_key': 'test-event-99',
            'line_ids': [
                (0, 0, {'account_id': self.company_data['default_account_receivable'].id, 'debit': 10.0}),
                (0, 0, {'account_id': self.company_data['default_account_revenue'].id, 'credit': 10.0}),
            ],
        })
        move.action_post()
        self.assertEqual(move.source_user_id, self.env.user)

    def test_report_supports_filters_and_xlsx_export(self):
        move = self.env['account.move'].create({
            'move_type': 'entry', 'journal_id': self.company_data['default_journal_misc'].id,
            'company_id': self.company_data['company'].id, 'date': '2026-05-01',
            'line_ids': [
                (0, 0, {'account_id': self.company_data['default_account_receivable'].id, 'debit': 15.0, 'partner_id': self.partner_a.id}),
                (0, 0, {'account_id': self.company_data['default_account_revenue'].id, 'credit': 15.0}),
            ],
        })
        move.action_post()
        wizard = self.env['financial.report.wizard'].create({
            'report_type': 'general_ledger', 'company_id': self.company_data['company'].id,
            'date_from': '2026-01-01', 'date_to': '2026-12-31',
            'account_ids': [(6, 0, [self.company_data['default_account_receivable'].id])],
            'partner_ids': [(6, 0, [self.partner_a.id])],
        })
        wizard.action_generate()
        self.assertTrue(wizard.line_ids.filtered(lambda line: line.move_id == move))
        action = wizard.action_export_xlsx()
        attachment_id = int(action['url'].split('/')[3].split('?')[0])
        attachment = self.env['ir.attachment'].browse(attachment_id)
        self.assertEqual(attachment.res_model, 'financial.report.wizard')

    def test_sales_inquiry_creates_one_quotation(self):
        product = self.env['product.product'].create({'name': 'Inquiry Product', 'list_price': 25.0})
        inquiry = self.env['custom.sales.inquiry'].create({
            'partner_id': self.partner_a.id,
            'line_ids': [(0, 0, {'product_id': product.id, 'quantity': 2, 'price_unit': 25.0})],
        })
        inquiry.action_accept()
        inquiry.action_accept()
        self.assertTrue(inquiry.quotation_id)
        self.assertEqual(self.env['sale.order'].search_count([('origin', '=', inquiry.name)]), 1)

    def test_custom_desk_requires_approved_configuration(self):
        product = self.env['product.product'].create({'name': 'Configured Desk', 'is_custom_desk': True, 'list_price': 100.0})
        order = self.env['sale.order'].create({'partner_id': self.partner_a.id})
        order.order_line.create({
            'order_id': order.id, 'product_id': product.id, 'name': product.name,
            'product_uom_qty': 1, 'product_uom': product.uom_id.id, 'price_unit': 100.0,
        })
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_ocr_rejects_unsupported_file(self):
        record = self.env['account.bill.digitization'].create({
            'company_id': self.company_data['company'].id,
            'document': base64.b64encode(b'not-supported'), 'document_filename': 'bill.exe',
            'provider': 'manual',
        })
        with self.assertRaises(ValidationError):
            record.action_run_extraction()

    def test_close_requires_checklist(self):
        close = self.env['custom.accounting.close'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2026-01-01', 'date_to': '2026-01-31',
        })
        close.action_run_checks()
        with self.assertRaises(ValidationError):
            close.action_approve()
