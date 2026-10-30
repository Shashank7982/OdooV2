from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMandatoryAnalytic(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env.ref('custom_accounting_analytic.analytic_plan_department')
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Sales Dept',
            'plan_id': cls.plan.id,
        })
        cls.company_data['default_account_expense'].require_analytic_distribution = True

    def _make_move(self, with_analytic):
        line_vals = {
            'account_id': self.company_data['default_account_expense'].id,
            'debit': 100.0, 'credit': 0.0,
        }
        if with_analytic:
            line_vals['analytic_distribution'] = {str(self.analytic_account.id): 100.0}
        return self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'company_id': self.company_data['company'].id,
            'date': '2026-03-01',
            'line_ids': [
                (0, 0, line_vals),
                (0, 0, {'account_id': self.company_data['default_account_payable'].id, 'debit': 0.0, 'credit': 100.0}),
            ],
        })

    def test_posting_blocked_without_analytic(self):
        move = self._make_move(with_analytic=False)
        with self.assertRaises(UserError):
            move.action_post()

    def test_posting_allowed_with_analytic(self):
        move = self._make_move(with_analytic=True)
        move.action_post()
        self.assertEqual(move.state, 'posted')

    def test_posting_allowed_when_flag_unset(self):
        self.company_data['default_account_expense'].require_analytic_distribution = False
        move = self._make_move(with_analytic=False)
        move.action_post()
        self.assertEqual(move.state, 'posted')
