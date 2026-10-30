from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountAsset(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        equity_account = cls.env['account.account'].search([
            *cls.env['account.account']._check_company_domain(cls.company_data['company']),
            ('account_type', 'in', ('equity', 'equity_unaffected')),
        ], limit=1)
        cls.category = cls.env['account.asset.category'].create({
            'name': 'Computer Equipment',
            'company_id': cls.company_data['company'].id,
            'method': 'linear',
            'duration_months': 12,
            'asset_account_id': cls.company_data['default_account_assets'].id,
            'depreciation_account_id': cls.company_data['default_account_assets'].id,
            'expense_account_id': cls.company_data['default_account_expense'].id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'revaluation_account_id': equity_account.id,
        })

    def _make_asset(self, purchase_value=1200.0, salvage_value=0.0):
        return self.env['account.asset'].create({
            'name': 'Laptop',
            'company_id': self.company_data['company'].id,
            'category_id': self.category.id,
            'purchase_date': '2026-01-01',
            'purchase_value': purchase_value,
            'salvage_value': salvage_value,
        })

    def test_straight_line_schedule_sums_to_depreciable_base(self):
        asset = self._make_asset(purchase_value=1200.0, salvage_value=0.0)
        asset.action_generate_schedule()
        self.assertEqual(asset.state, 'running')
        self.assertEqual(len(asset.depreciation_line_ids), 12)
        self.assertEqual(round(sum(asset.depreciation_line_ids.mapped('amount')), 2), 1200.0)

    def test_dispose_zeroes_book_value_and_posts_balanced_move(self):
        asset = self._make_asset(purchase_value=1200.0)
        asset.action_generate_schedule()
        asset.action_dispose()
        self.assertEqual(asset.state, 'disposed')
        self.assertEqual(round(asset.book_value, 2), 0.0)
        last_line = asset.depreciation_line_ids.sorted('sequence')[-1]
        self.assertTrue(last_line.posted)
        move = last_line.move_id
        self.assertEqual(sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')))

    def test_sell_wizard_books_gain(self):
        asset = self._make_asset(purchase_value=1200.0)
        asset.action_generate_schedule()
        wizard = self.env['account.asset.sale.wizard'].create({
            'asset_id': asset.id,
            'sale_price': 1500.0,
            'proceeds_account_id': self.company_data['default_account_receivable'].id,
        })
        wizard.action_confirm()
        self.assertEqual(asset.state, 'sold')
        self.assertEqual(round(asset.book_value, 2), 0.0)

    def test_sell_wizard_books_loss(self):
        asset = self._make_asset(purchase_value=1200.0)
        asset.action_generate_schedule()
        wizard = self.env['account.asset.sale.wizard'].create({
            'asset_id': asset.id,
            'sale_price': 200.0,
            'proceeds_account_id': self.company_data['default_account_receivable'].id,
        })
        wizard.action_confirm()
        self.assertEqual(asset.state, 'sold')

    def test_revaluation_wizard_updates_book_value(self):
        asset = self._make_asset(purchase_value=1200.0)
        asset.action_generate_schedule()
        wizard = self.env['account.asset.revaluation.wizard'].create({
            'asset_id': asset.id,
            'new_value': 2000.0,
        })
        wizard.action_confirm()
        self.assertEqual(round(asset.book_value, 2), 2000.0)
