from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCashTransactions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cash Test Customer', 'l10n_in_pan': 'ABCDE1234F',
        })
        cls.cash_account = cls.env['account.account'].create({
            'name': 'Cash Test Account', 'code': '109901',
            'account_type': 'asset_cash', 'reconcile': True,
            'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.income_account = cls.env['account.account'].create({
            'name': 'Cash Test Sales', 'code': '409901',
            'account_type': 'income', 'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Cash Test Expense', 'code': '609901',
            'account_type': 'expense', 'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.cash_journal = cls.env['account.journal'].create({
            'name': 'Cash Test Journal', 'code': 'CTJ', 'type': 'cash',
            'default_account_id': cls.cash_account.id,
            'company_id': cls.company.id,
        })
        (cls.cash_journal.inbound_payment_method_line_ids | cls.cash_journal.outbound_payment_method_line_ids).write({
            'payment_account_id': cls.cash_account.id,
        })
        cls.sale_journal = cls.env['account.journal'].create({
            'name': 'Cash Test Sales Journal', 'code': 'CTS', 'type': 'sale',
            'company_id': cls.company.id,
        })
        cls.location = cls.env['account.cash.location'].create({
            'name': 'Cash Test Location', 'company_id': cls.company.id,
            'journal_id': cls.cash_journal.id, 'custodian_id': cls.env.user.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Cash Test Product', 'list_price': 100.0,
        })

    def _create_invoice(self):
        return self.env['account.move'].create({
            'move_type': 'out_invoice', 'journal_id': self.sale_journal.id,
            'partner_id': self.partner.id,
            'invoice_date': fields.Date.today(),
            'transaction_mode': 'cash', 'cash_journal_id': self.cash_journal.id,
            'cash_location_id': self.location.id, 'cash_payment_method': 'cash',
            'cash_receipt_ref': 'TEST-CASH-001',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id, 'name': 'Cash test sale',
                'quantity': 1, 'price_unit': 100,
                'account_id': self.income_account.id,
            })],
        })

    def test_cash_invoice_posts_and_settles(self):
        invoice = self._create_invoice()
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertTrue(invoice.cash_payment_id)
        self.assertEqual(invoice.cash_payment_id.journal_id, self.cash_journal)
        self.assertAlmostEqual(invoice.amount_residual, 0.0, places=2)

    def test_cash_invoice_requires_journal(self):
        invoice = self._create_invoice()
        with self.assertRaises(ValidationError):
            invoice.write({'cash_journal_id': False})

    def test_petty_cash_voucher_creates_posted_move(self):
        voucher = self.env['account.petty.cash.voucher'].create({
            'date': fields.Date.today(), 'location_id': self.location.id,
            'payee_name': 'Office Supplier', 'purpose': 'Stationery',
            'expense_account_id': self.expense_account.id, 'amount': 25.0,
        })
        voucher.action_submit()
        voucher.action_approve()
        voucher.action_post()
        self.assertEqual(voucher.state, 'posted')
        self.assertEqual(voucher.move_id.state, 'posted')
        self.assertEqual(voucher.move_id.cash_location_id, self.location)

    def test_cash_book_contains_posted_cash_invoice(self):
        invoice = self._create_invoice()
        invoice.action_post()
        payment_move = invoice.cash_payment_id.move_id
        self.assertEqual(payment_move.cash_location_id, self.location)
        self.assertTrue(
            payment_move.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_cash'),
            repr([(line.account_id.code, line.account_id.account_type, line.debit, line.credit) for line in payment_move.line_ids]),
        )
        wizard = self.env['cash.book.report.wizard'].create({
            'company_id': self.company.id,
            'date_from': fields.Date.today(), 'date_to': fields.Date.today(),
            'journal_ids': [(6, 0, [self.cash_journal.id])],
            'location_id': self.location.id, 'transaction_mode': 'cash',
        })
        wizard.action_generate()
        self.assertTrue(wizard.line_ids)
        self.assertTrue(any(line.move_id == payment_move for line in wizard.line_ids))
