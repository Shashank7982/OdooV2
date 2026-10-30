from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountingDashboard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'company_id': cls.company_data['company'].id,
            'date': '2026-04-01',
            'line_ids': [
                (0, 0, {
                    'account_id': cls.company_data['default_account_receivable'].id,
                    'partner_id': cls.partner_a.id, 'debit': 500.0, 'credit': 0.0,
                }),
                (0, 0, {'account_id': cls.company_data['default_account_revenue'].id, 'debit': 0.0, 'credit': 500.0}),
            ],
        })
        move.action_post()

    def test_dashboard_refresh_computes_without_error(self):
        wizard = self.env['accounting.dashboard'].create({
            'company_id': self.company_data['company'].id,
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
        })
        wizard.action_refresh()
        self.assertGreaterEqual(wizard.total_receivable, 500.0)
        self.assertGreaterEqual(wizard.total_payable, 0.0)
        self.assertGreaterEqual(wizard.monthly_revenue, 500.0)

    def test_dashboard_reports_optional_module_flags(self):
        wizard = self.env['accounting.dashboard'].create({
            'company_id': self.company_data['company'].id,
        })
        wizard.action_refresh()
        self.assertEqual(wizard.gst_module_installed, 'gstr3b.report.wizard' in self.env)
        self.assertEqual(wizard.budget_module_installed, 'account.budget' in self.env)
