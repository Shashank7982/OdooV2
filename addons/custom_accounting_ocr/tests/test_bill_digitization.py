import base64

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBillDigitization(AccountTestInvoicingCommon):

    def _make_record(self, invoice_number='INV-1001'):
        return self.env['account.bill.digitization'].create({
            'company_id': self.company_data['company'].id,
            'document': base64.b64encode(b'fake-pdf-bytes'),
            'document_filename': 'bill.pdf',
            'provider': 'manual',
            'partner_id': self.partner_a.id,
            'invoice_number': invoice_number,
            'total_amount': 118.0,
            'tax_amount': 18.0,
        })

    def test_confirm_requires_partner_and_total(self):
        record = self.env['account.bill.digitization'].create({
            'company_id': self.company_data['company'].id,
            'document': base64.b64encode(b'fake-pdf-bytes'),
            'provider': 'manual',
        })
        with self.assertRaises(UserError):
            record.action_confirm()

    def test_no_auto_post_without_confirm(self):
        record = self._make_record()
        with self.assertRaises(UserError):
            record.action_create_vendor_bill()
        self.assertFalse(record.vendor_bill_id)

    def test_manual_confirm_then_create_bill_keeps_document_attached(self):
        record = self._make_record()
        record.action_confirm()
        self.assertEqual(record.state, 'confirmed')
        record.action_create_vendor_bill()
        self.assertEqual(record.state, 'posted')
        self.assertTrue(record.vendor_bill_id)
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'), ('res_id', '=', record.vendor_bill_id.id),
        ])
        self.assertTrue(attachment)

    def test_duplicate_invoice_number_detected(self):
        first = self._make_record(invoice_number='DUP-1')
        first.action_confirm()
        first.action_create_vendor_bill()

        second = self._make_record(invoice_number='DUP-1')
        self.assertTrue(second.duplicate_warning)
