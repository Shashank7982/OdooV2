import datetime

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestFollowup(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # isolate from any demo-data follow-up levels shipped by the module
        cls.env['account.followup.level'].search([]).unlink()
        cls.level_15 = cls.env['account.followup.level'].create({
            'name': 'Reminder', 'delay_days': 15, 'action': 'email',
        })
        cls.level_30 = cls.env['account.followup.level'].create({
            'name': 'Second Notice', 'delay_days': 30, 'action': 'email',
        })
        cls.level_60 = cls.env['account.followup.level'].create({
            'name': 'Final Notice', 'delay_days': 60, 'action': 'email',
        })

    def _make_overdue_invoice(self, days_overdue):
        due_date = fields.Date.context_today(self.env['res.partner']) - datetime.timedelta(days=days_overdue)
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.company_data['default_journal_misc'].id,
            'company_id': self.company_data['company'].id,
            'date': due_date,
            'line_ids': [
                (0, 0, {
                    'account_id': self.company_data['default_account_receivable'].id,
                    'partner_id': self.partner_a.id,
                    'debit': 100.0, 'credit': 0.0,
                    'date_maturity': due_date,
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 0.0, 'credit': 100.0,
                }),
            ],
        })
        move.action_post()
        return move

    def test_level_selected_by_days_overdue(self):
        self._make_overdue_invoice(35)
        self.assertGreaterEqual(self.partner_a.max_overdue_days, 35)
        self.partner_a._trigger_followup(force=True)
        self.assertEqual(self.partner_a.followup_level_id, self.level_30)

    def test_no_level_when_not_overdue_enough(self):
        self._make_overdue_invoice(5)
        self.partner_a._trigger_followup(force=True)
        self.assertFalse(self.partner_a.followup_level_id)

    def test_highest_matching_level_selected(self):
        self._make_overdue_invoice(90)
        self.partner_a._trigger_followup(force=True)
        self.assertEqual(self.partner_a.followup_level_id, self.level_60)
