import base64
import io

import openpyxl

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBankStatementCsvImportWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_journal = cls.company_data['default_journal_bank']

    def _make_wizard(self, csv_content, date_format='%Y-%m-%d'):
        return self.env['bank.statement.csv.import.wizard'].create({
            'journal_id': self.bank_journal.id,
            'csv_file': base64.b64encode(csv_content.encode('utf-8')),
            'csv_filename': 'statement.csv',
            'date_format': date_format,
        })

    def test_import_creates_statement_lines(self):
        csv_content = (
            "date,label,amount,partner_name,reference\n"
            "2026-01-05,Payment received,1500.00,partner_a,INV/001\n"
            "2026-01-06,Office supplies,-200.50,,REF-2\n"
        )
        wizard = self._make_wizard(csv_content)
        wizard.action_import()
        self.assertEqual(wizard.imported_count, 2)
        lines = self.env['account.bank.statement.line'].search([('journal_id', '=', self.bank_journal.id)])
        self.assertEqual(len(lines), 2)
        amounts = sorted(lines.mapped('amount'))
        self.assertEqual(amounts, [-200.50, 1500.00])

    def test_import_matches_partner_by_name(self):
        csv_content = (
            "date,label,amount,partner_name\n"
            f"2026-01-05,Payment,1000.00,{self.partner_a.name}\n"
        )
        wizard = self._make_wizard(csv_content)
        wizard.action_import()
        line = self.env['account.bank.statement.line'].search([('journal_id', '=', self.bank_journal.id)], limit=1)
        self.assertEqual(line.partner_id, self.partner_a)

    def test_missing_required_columns_raises(self):
        wizard = self._make_wizard("foo,bar\n1,2\n")
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_bad_row_blocks_atomic_import(self):
        csv_content = (
            "date,label,amount\n"
            "not-a-date,Bad row,100\n"
            "2026-01-06,Good row,50\n"
        )
        wizard = self._make_wizard(csv_content)
        with self.assertRaises(UserError):
            wizard.action_import()
        self.assertEqual(wizard.imported_count, 0)
        self.assertFalse(self.env['account.bank.statement.line'].search([
            ('journal_id', '=', self.bank_journal.id), ('payment_ref', '=', 'Good row'),
        ]))

    def test_duplicate_rows_are_skipped_on_reimport(self):
        csv_content = (
            "date,label,amount\n"
            "2026-01-05,Payment received,1500.00\n"
        )
        wizard1 = self._make_wizard(csv_content)
        wizard1.action_import()
        self.assertEqual(wizard1.imported_count, 1)

        wizard2 = self._make_wizard(csv_content)
        wizard2.action_import()
        self.assertEqual(wizard2.imported_count, 0)
        self.assertEqual(wizard2.skipped_count, 1)

        lines = self.env['account.bank.statement.line'].search([('journal_id', '=', self.bank_journal.id)])
        self.assertEqual(len(lines), 1)

    def test_download_csv_template_matches_parser_columns(self):
        wizard = self._make_wizard("date,label,amount\n2026-01-05,x,1\n")
        action = wizard.action_download_template()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        attachment = self.env['ir.attachment'].browse(int(action['url'].split('/')[-1].split('?')[0]))
        content = base64.b64decode(attachment.datas).decode('utf-8-sig')
        header = content.splitlines()[0]
        self.assertEqual(header, 'date,label,amount,partner_name,reference')

    def test_downloaded_csv_template_actually_imports(self):
        """ The template's own example row must be parseable by action_import
        (columns/format in sync) - it will import as one transaction since
        the wizard doesn't know it's an "example". """
        wizard = self._make_wizard("date,label,amount\n2026-01-05,x,1\n")
        action = wizard.action_download_template()
        attachment = self.env['ir.attachment'].browse(int(action['url'].split('/')[-1].split('?')[0]))
        wizard2 = self._make_wizard('')
        wizard2.csv_file = attachment.datas
        wizard2.action_import()
        self.assertEqual(wizard2.imported_count, 1)
        self.assertEqual(wizard2.error_count, 0)

    def test_download_xlsx_template(self):
        wizard = self._make_wizard("date,label,amount\n2026-01-05,x,1\n")
        action = wizard.action_download_template_xlsx()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        attachment = self.env['ir.attachment'].browse(int(action['url'].split('/')[-1].split('?')[0]))
        content = base64.b64decode(attachment.datas)
        self.assertTrue(content.startswith(b'PK'), 'Should be a real XLSX (zip) file')

    def test_semicolon_delimiter(self):
        csv_content = (
            "date;label;amount\n"
            "2026-01-05;Payment received;1500.00\n"
        )
        wizard = self.env['bank.statement.csv.import.wizard'].create({
            'journal_id': self.bank_journal.id,
            'csv_file': base64.b64encode(csv_content.encode('utf-8')),
            'csv_filename': 'statement.csv',
            'date_format': '%Y-%m-%d',
            'delimiter': ';',
        })
        wizard.action_import()
        self.assertEqual(wizard.imported_count, 1)

    def test_xlsx_preview_and_import(self):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Bank Transactions'
        sheet.append(['date', 'label', 'amount', 'partner_name', 'reference'])
        sheet.append(['2026-01-05', 'XLSX payment', 750.0, self.partner_a.name, 'XLSX-1'])
        buffer = io.BytesIO()
        workbook.save(buffer)
        wizard = self.env['bank.statement.csv.import.wizard'].create({
            'journal_id': self.bank_journal.id,
            'csv_file': base64.b64encode(buffer.getvalue()),
            'csv_filename': 'statement.xlsx',
            'date_format': '%Y-%m-%d',
        })
        wizard.action_preview()
        self.assertEqual(len(wizard.preview_line_ids), 1)
        self.assertEqual(wizard.preview_line_ids.status, 'ready')
        wizard.action_import()
        self.assertEqual(wizard.imported_count, 1)
