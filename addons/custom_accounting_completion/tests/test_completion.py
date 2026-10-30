import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountingPlanCompletion(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Completion records are intentionally protected by the suite's
        # role-based ACLs. Give the Odoo test user the same role a real
        # accounting operator would receive in production.
        manager_group = cls.env.ref(
            'custom_accounting_security.group_accounting_manager',
            raise_if_not_found=False,
        )
        if manager_group:
            cls.env.user.sudo().write({'groups_id': [(4, manager_group.id)]})

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

    def test_sales_invoice_requires_product_line(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': self.company_data['default_journal_sale'].id,
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Unmapped line', 'quantity': 1, 'price_unit': 50.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        with self.assertRaises(ValidationError):
            invoice.action_post()
        self.assertEqual(invoice.state, 'draft')

    def test_contract_release_creates_linked_sales_order(self):
        product = self.env['product.product'].create({'name': 'Contract Product', 'list_price': 40.0})
        contract = self.env['custom.sales.contract'].create({
            'partner_id': self.partner_a.id,
            'start_date': '2026-01-01',
            'line_ids': [(0, 0, {
                'product_id': product.id, 'quantity': 2, 'price_unit': 40.0,
            })],
        })
        contract.action_activate()
        action = contract.action_release_order()
        order = self.env['sale.order'].browse(action['res_id'])
        self.assertEqual(order.custom_contract_id, contract)
        self.assertEqual(order.order_line.product_id, product)

    def test_waybill_validation_records_actor_and_time(self):
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'), ('company_id', '=', self.company_data['company'].id),
        ], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'partner_id': self.partner_a.id,
            'company_id': self.company_data['company'].id,
        })
        waybill = self.env['custom.sales.waybill'].create({
            'picking_id': picking.id,
        })
        waybill.action_request()
        waybill.number = 'EWB-TEST-001'
        waybill.action_validate()
        self.assertEqual(waybill.state, 'received')
        self.assertEqual(waybill.validated_by, self.env.user)
        self.assertTrue(waybill.validated_at)

    def test_year_close_prepares_opening_entry(self):
        revenue = self.company_data['default_account_revenue']
        receivable = self.company_data['default_account_receivable']
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'company_id': self.company_data['company'].id,
            'date': '2026-12-15',
            'line_ids': [
                (0, 0, {'account_id': receivable.id, 'debit': 100.0, 'partner_id': self.partner_a.id}),
                (0, 0, {'account_id': revenue.id, 'credit': 100.0}),
            ],
        })
        move.action_post()
        retained = self.env['account.account'].search([
            ('company_ids', 'in', self.company_data['company'].id),
            ('account_type', '=', 'equity_unaffected'),
        ], limit=1)
        close = self.env['custom.accounting.close'].create({
            'company_id': self.company_data['company'].id,
            'close_type': 'year', 'date_from': '2026-01-01', 'date_to': '2026-12-31',
            'journal_id': self.company_data['default_journal_misc'].id,
            'retained_earnings_account_id': retained.id,
            'sales_reviewed': True, 'purchase_reviewed': True, 'bank_reconciled': True,
            'asset_deferred_reviewed': True, 'reports_reviewed': True,
            'controller_approved': True,
        })
        close.action_run_checks()
        close.action_approve()
        close.action_generate_closing_entry()
        close.action_lock()
        close.action_prepare_next_year()
        self.assertTrue(close.opening_move_id)
        self.assertEqual(close.opening_move_id.state, 'posted')
        self.assertTrue(close.carryforward_done)
