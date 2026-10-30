from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestFinancialReportWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'company_id': cls.company_data['company'].id,
            'date': '2026-03-01',
            'line_ids': [
                (0, 0, {'account_id': cls.company_data['default_account_receivable'].id, 'debit': 1000.0, 'credit': 0.0, 'partner_id': cls.partner_a.id}),
                (0, 0, {'account_id': cls.company_data['default_account_revenue'].id, 'debit': 0.0, 'credit': 1000.0}),
            ],
        })
        move.action_post()
        cls.move = move

    def _wizard(self, report_type):
        return self.env['financial.report.wizard'].create({
            'report_type': report_type,
            'company_id': self.company_data['company'].id,
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
        })

    def test_trial_balance_is_balanced(self):
        wizard = self._wizard('trial_balance')
        wizard.action_generate()
        self.assertEqual(round(wizard.total_debit, 2), round(wizard.total_credit, 2))
        self.assertTrue(wizard.line_ids)

    def test_profit_loss_runs_and_has_net_line(self):
        wizard = self._wizard('profit_loss')
        wizard.action_generate()
        net_line = wizard.line_ids.filtered(lambda l: l.label == 'NET PROFIT / (LOSS)')
        self.assertTrue(net_line)
        self.assertEqual(round(net_line.balance, 2), 1000.0)

    def test_balance_sheet_balances(self):
        wizard = self._wizard('balance_sheet')
        wizard.action_generate()
        total_assets = wizard.line_ids.filtered(lambda l: l.label == 'Total Assets')
        total_le = wizard.line_ids.filtered(lambda l: l.label == 'Total Liabilities + Equity')
        self.assertTrue(total_assets)
        self.assertTrue(total_le)
        self.assertEqual(round(total_assets.balance, 2), round(total_le.balance, 2))

    def test_drilldown_action_returns_matching_lines(self):
        wizard = self._wizard('trial_balance')
        wizard.action_generate()
        receivable_line = wizard.line_ids.filtered(
            lambda l: l.account_id == self.company_data['default_account_receivable'])
        self.assertTrue(receivable_line)
        action = receivable_line.action_view_journal_items()
        found = self.env['account.move.line'].search(action['domain'])
        self.assertIn(self.move.id, found.move_id.ids)
