from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDeferredSchedule(AccountTestInvoicingCommon):

    def _make_schedule(self, deferred_type='revenue', total_amount=1200.0):
        return self.env['account.deferred.schedule'].create({
            'name': 'Annual Support Contract',
            'company_id': self.company_data['company'].id,
            'deferred_type': deferred_type,
            'journal_id': self.company_data['default_journal_misc'].id,
            'source_account_id': (
                self.company_data['default_account_deferred_revenue']
                if deferred_type == 'revenue' else self.company_data['default_account_deferred_expense']
            ).id,
            'target_account_id': (
                self.company_data['default_account_revenue']
                if deferred_type == 'revenue' else self.company_data['default_account_expense']
            ).id,
            'total_amount': total_amount,
            'start_date': '2026-01-01',
            'end_date': '2026-12-01',
        })

    def test_schedule_totals_equal_original_amount(self):
        schedule = self._make_schedule(total_amount=1200.0)
        schedule.action_generate_schedule()
        self.assertEqual(schedule.state, 'running')
        self.assertEqual(len(schedule.line_ids), 12)
        self.assertEqual(round(sum(schedule.line_ids.mapped('amount')), 2), 1200.0)

    def test_early_termination_recognizes_remaining_balance(self):
        schedule = self._make_schedule(total_amount=1200.0)
        schedule.action_generate_schedule()
        # simulate one posted line already recognized
        first_line = schedule.line_ids.sorted('sequence')[0]
        first_line._post_entry()
        self.assertGreater(schedule.remaining_amount, 0)
        schedule.action_terminate_early()
        self.assertEqual(schedule.state, 'terminated')
        self.assertEqual(round(schedule.remaining_amount, 2), 0.0)

    def test_expense_schedule_generation(self):
        schedule = self._make_schedule(deferred_type='expense', total_amount=600.0)
        schedule.action_generate_schedule()
        self.assertEqual(round(sum(schedule.line_ids.mapped('amount')), 2), 600.0)
