from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestOpeningBalanceWizard(AccountTestInvoicingCommon):

    def test_balanced_opening_entry_created(self):
        wizard = self.env['account.opening.balance.wizard'].create({
            'company_id': self.company_data['company'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'account_id': self.company_data['default_account_revenue'].id, 'debit': 0.0, 'credit': 500.0}),
                (0, 0, {'account_id': self.company_data['default_account_expense'].id, 'debit': 500.0, 'credit': 0.0}),
            ],
        })
        self.assertTrue(wizard.is_balanced)
        action = wizard.action_create_opening_entry()
        move = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')))
        self.assertEqual(move.ref, 'Opening Balance')

    def test_unbalanced_opening_entry_blocked(self):
        wizard = self.env['account.opening.balance.wizard'].create({
            'company_id': self.company_data['company'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'account_id': self.company_data['default_account_revenue'].id, 'debit': 0.0, 'credit': 500.0}),
            ],
        })
        self.assertFalse(wizard.is_balanced)
        with self.assertRaises(UserError):
            wizard.action_create_opening_entry()

    def test_empty_lines_blocked(self):
        wizard = self.env['account.opening.balance.wizard'].create({
            'company_id': self.company_data['company'].id,
            'journal_id': self.company_data['default_journal_misc'].id,
        })
        with self.assertRaises(UserError):
            wizard.action_create_opening_entry()
