from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountBudget(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env['account.analytic.plan'].create({'name': 'Budget Test Plan'})
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Marketing',
            'plan_id': cls.plan.id,
        })
        expense_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'company_id': cls.company_data['company'].id,
            'date': '2026-02-10',
            'line_ids': [
                (0, 0, {
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 800.0, 'credit': 0.0,
                    'analytic_distribution': {str(cls.analytic_account.id): 100.0},
                }),
                (0, 0, {
                    'account_id': cls.company_data['default_account_payable'].id,
                    'debit': 0.0, 'credit': 800.0,
                }),
            ],
        })
        expense_move.action_post()

    def _make_budget(self, budgeted_amount=1000.0):
        return self.env['account.budget'].create({
            'name': 'Marketing 2026',
            'company_id': self.company_data['company'].id,
            'analytic_account_id': self.analytic_account.id,
            'budget_type': 'expense',
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'budgeted_amount': budgeted_amount,
        })

    def test_actual_amount_matches_posted_moves(self):
        budget = self._make_budget()
        self.assertEqual(round(budget.actual_amount, 2), 800.0)

    def test_variance_math(self):
        budget = self._make_budget(budgeted_amount=1000.0)
        self.assertEqual(round(budget.variance_amount, 2), -200.0)
        self.assertEqual(round(budget.variance_percent, 2), -20.0)
        self.assertEqual(round(budget.remaining_amount, 2), 200.0)

    def test_confirm_requires_analytic_account(self):
        budget = self.env['account.budget'].create({
            'name': 'No Analytic',
            'company_id': self.company_data['company'].id,
            'budget_type': 'expense',
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'budgeted_amount': 500.0,
        })
        with self.assertRaises(UserError):
            budget.action_confirm()

    def test_confirm_succeeds_with_analytic_account(self):
        budget = self._make_budget()
        budget.action_confirm()
        self.assertEqual(budget.state, 'confirmed')
