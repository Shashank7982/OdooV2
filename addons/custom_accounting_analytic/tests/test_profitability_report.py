from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProfitabilityReportWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env.ref('custom_accounting_analytic.analytic_plan_project')
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Project X',
            'plan_id': cls.plan.id,
        })
        revenue_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'company_id': cls.company_data['company'].id,
            'date': '2026-03-01',
            'line_ids': [
                (0, 0, {
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'debit': 1000.0, 'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 0.0, 'credit': 1000.0,
                    'analytic_distribution': {str(cls.analytic_account.id): 100.0},
                }),
            ],
        })
        revenue_move.action_post()
        expense_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'company_id': cls.company_data['company'].id,
            'date': '2026-03-05',
            'line_ids': [
                (0, 0, {
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 400.0, 'credit': 0.0,
                    'analytic_distribution': {str(cls.analytic_account.id): 100.0},
                }),
                (0, 0, {
                    'account_id': cls.company_data['default_account_payable'].id,
                    'debit': 0.0, 'credit': 400.0,
                }),
            ],
        })
        expense_move.action_post()

    def test_profitability_by_analytic_account(self):
        wizard = self.env['profitability.report.wizard'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
            'group_by': 'analytic',
        })
        wizard.action_generate()
        line = wizard.line_ids.filtered(lambda l: l.analytic_account_id == self.analytic_account)
        self.assertTrue(line)
        self.assertEqual(round(line.revenue, 2), 1000.0)
        self.assertEqual(round(line.opex, 2), 400.0)
        self.assertEqual(round(line.net_profit, 2), 600.0)
