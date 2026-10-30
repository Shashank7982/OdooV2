from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRecurringEntry(AccountTestInvoicingCommon):

    def test_generate_move_is_balanced(self):
        template = self.env['account.recurring.entry'].create({
            'name': 'Rent',
            'company_id': self.company_data['company'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'frequency': 'monthly',
            'line_ids': [
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'name': 'Rent expense', 'debit': 1000.0, 'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_payable'].id,
                    'name': 'Rent payable', 'debit': 0.0, 'credit': 1000.0,
                }),
            ],
        })
        self.assertTrue(template.is_balanced)
        move = template._generate_move()
        self.assertEqual(sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')))
        self.assertEqual(move.recurring_entry_id, template)

    def test_generate_move_unbalanced_raises(self):
        template = self.env['account.recurring.entry'].create({
            'name': 'Unbalanced',
            'company_id': self.company_data['company'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'frequency': 'monthly',
            'line_ids': [
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'name': 'Line', 'debit': 1000.0, 'credit': 0.0,
                }),
            ],
        })
        self.assertFalse(template.is_balanced)
        with self.assertRaises(UserError):
            template._generate_move()

    def test_next_date_advances_by_frequency(self):
        template = self.env['account.recurring.entry'].create({
            'name': 'Quarterly',
            'company_id': self.company_data['company'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'frequency': 'quarterly',
            'next_date': '2026-01-15',
            'line_ids': [
                (0, 0, {'account_id': self.company_data['default_account_expense'].id, 'debit': 100.0, 'credit': 0.0}),
                (0, 0, {'account_id': self.company_data['default_account_payable'].id, 'debit': 0.0, 'credit': 100.0}),
            ],
        })
        template._generate_move()
        self.assertEqual(str(template.next_date), '2026-04-15')
