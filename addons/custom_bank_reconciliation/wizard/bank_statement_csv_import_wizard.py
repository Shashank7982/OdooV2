import base64
import csv
import datetime
import io

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill
except ImportError:  # pragma: no cover
    openpyxl = None

TEMPLATE_COLUMNS = ['date', 'label', 'amount', 'partner_name', 'reference']


class BankStatementCsvImportWizard(models.TransientModel):
    _name = 'bank.statement.csv.import.wizard'
    _description = 'Bank Statement CSV Import'

    journal_id = fields.Many2one(
        'account.journal',
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="The bank/cash journal these transactions belong to.")
    csv_file = fields.Binary(string='Statement File (CSV/XLSX)')
    csv_filename = fields.Char()
    file_type = fields.Selection([
        ('csv', 'CSV'),
        ('xlsx', 'XLSX'),
    ], compute='_compute_file_type', store=True)
    date_format = fields.Selection([
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%Y-%m-%d', 'YYYY-MM-DD'),
        ('%m/%d/%Y', 'MM/DD/YYYY'),
    ], default='%d/%m/%Y', required=True)
    delimiter = fields.Selection([
        (',', 'Comma ( , )'),
        (';', 'Semicolon ( ; )'),
        ('\t', 'Tab'),
        ('|', 'Pipe ( | )'),
    ], default=',', required=True)
    skip_duplicates = fields.Boolean(
        default=True,
        help="Skip a row if a transaction with the same journal, date, amount and "
             "label already exists — protects against importing the same file twice.")

    import_log = fields.Text(readonly=True)
    imported_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    error_count = fields.Integer(readonly=True)
    imported_total = fields.Monetary(readonly=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    preview_state = fields.Selection([
        ('empty', 'Not Previewed'),
        ('ready', 'Preview Ready'),
        ('imported', 'Imported'),
    ], default='empty', readonly=True)
    preview_line_ids = fields.One2many(
        'bank.statement.csv.import.line', 'wizard_id', string='Preview Lines', copy=False,
    )

    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.journal_id.currency_id or wizard.journal_id.company_id.currency_id

    @api.depends('csv_filename')
    def _compute_file_type(self):
        for wizard in self:
            filename = (wizard.csv_filename or '').lower()
            wizard.file_type = 'xlsx' if filename.endswith(('.xlsx', '.xlsm')) else 'csv'

    def _is_duplicate(self, date_value, amount, label):
        return bool(self.env['account.bank.statement.line'].search_count([
            ('journal_id', '=', self.journal_id.id),
            ('date', '=', date_value),
            ('amount', '=', amount),
            ('payment_ref', '=', label),
        ], limit=1))

    def _parse_date(self, value):
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        value = str(value or '').strip()
        if not value:
            raise UserError(_('Date is required.'))
        try:
            return datetime.datetime.strptime(value, self.date_format).date()
        except ValueError:
            # Accept ISO dates in spreadsheets even when the display format is
            # configured differently; this is common when exporting from a bank.
            return datetime.date.fromisoformat(value)

    def _rows_from_csv(self, raw):
        content = raw.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(content), delimiter=self.delimiter)
        if not reader.fieldnames:
            raise UserError(_('The CSV file has no header row.'))
        return reader.fieldnames, list(enumerate(reader, start=2))

    def _rows_from_xlsx(self, raw):
        if openpyxl is None:
            raise UserError(_('openpyxl is required to import XLSX bank statements.'))
        workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        sheet = workbook['Bank Transactions'] if 'Bank Transactions' in workbook.sheetnames else workbook.active
        rows = sheet.iter_rows(values_only=True)
        try:
            headers = [str(value or '').strip() for value in next(rows)]
        except StopIteration as error:
            raise UserError(_('The XLSX file has no header row.')) from error
        return headers, [
            (row_number, dict(zip(headers, values)))
            for row_number, values in enumerate(rows, start=2)
            if any(value not in (None, '') for value in values)
        ]

    def _parse_preview_rows(self):
        self.ensure_one()
        raw = base64.b64decode(self.csv_file)
        if self.file_type == 'xlsx':
            headers, rows = self._rows_from_xlsx(raw)
        else:
            headers, rows = self._rows_from_csv(raw)
        fieldmap = {str(column).strip().lower(): column for column in headers}
        required_cols = {'date', 'label', 'amount'}
        missing = required_cols - set(fieldmap)
        if missing:
            raise UserError(_(
                'The file must contain date, label, and amount columns. Missing: %s',
                ', '.join(sorted(missing)),
            ))

        parsed = []
        seen = set()
        for row_number, row in rows:
            values = {
                'row_number': row_number,
                'partner_name': str(row.get(fieldmap.get('partner_name'), '') or '').strip(),
                'reference': str(row.get(fieldmap.get('reference'), '') or '').strip(),
            }
            try:
                values['date'] = self._parse_date(row.get(fieldmap['date']))
                values['label'] = str(row.get(fieldmap['label'], '') or '').strip()
                if not values['label']:
                    raise UserError(_('Label is required.'))
                values['amount'] = float(row.get(fieldmap['amount']))
                if not values['amount']:
                    raise UserError(_('Amount must not be zero.'))
                partner = False
                if values['partner_name']:
                    partner = self.env['res.partner'].search(
                        [('name', 'ilike', values['partner_name'])], limit=1)
                values['partner_id'] = partner.id if partner else False
                duplicate_key = (values['date'], values['amount'], values['label'])
                is_duplicate = duplicate_key in seen or self._is_duplicate(*duplicate_key)
                seen.add(duplicate_key)
                if is_duplicate:
                    values.update({
                        'status': 'duplicate',
                        'error_message': _('This row duplicates an existing or earlier statement line.'),
                    })
                    if not self.skip_duplicates:
                        values['status'] = 'error'
                else:
                    values['status'] = 'ready'
            except Exception as error:
                values.update({'status': 'error', 'error_message': str(error)})
            parsed.append(values)
        return parsed

    def action_preview(self):
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_('Please select a journal.'))
        if not self.csv_file:
            raise UserError(_('Please attach a CSV or XLSX file.'))
        self.preview_line_ids.unlink()
        values = self._parse_preview_rows()
        self.env['bank.statement.csv.import.line'].create([
            dict(value, wizard_id=self.id) for value in values
        ])
        self.write({
            'preview_state': 'ready',
            'import_log': _('Preview generated: %s row(s) ready, %s duplicate(s), %s error(s).') % (
                len(self.preview_line_ids.filtered(lambda line: line.status == 'ready')),
                len(self.preview_line_ids.filtered(lambda line: line.status == 'duplicate')),
                len(self.preview_line_ids.filtered(lambda line: line.status == 'error')),
            ),
            'imported_count': 0,
            'skipped_count': len(self.preview_line_ids.filtered(lambda line: line.status == 'duplicate')),
            'error_count': len(self.preview_line_ids.filtered(lambda line: line.status == 'error')),
            'imported_total': 0.0,
        })
        return {
            'type': 'ir.actions.act_window', 'res_model': self._name,
            'res_id': self.id, 'view_mode': 'form', 'target': 'new',
        }

    def action_import(self):
        self.ensure_one()
        if self.preview_state != 'ready':
            self.action_preview()
        errors = self.preview_line_ids.filtered(lambda line: line.status == 'error')
        if errors:
            raise UserError(_(
                'Import blocked: correct all %s preview error(s) before importing. '
                'No statement lines were created.', len(errors),
            ))
        ready = self.preview_line_ids.filtered(lambda line: line.status == 'ready')
        vals_list = [{
            'journal_id': self.journal_id.id,
            'date': line.date,
            'payment_ref': line.label,
            'amount': line.amount,
            'partner_id': line.partner_id.id or False,
            'ref': line.reference,
        } for line in ready]
        # One create call is intentional: if any database constraint fails,
        # the Odoo transaction rolls back the complete import batch.
        self.env['account.bank.statement.line'].create(vals_list)
        total = sum(ready.mapped('amount'))
        self.write({
            'preview_state': 'imported',
            'imported_count': len(ready),
            'skipped_count': len(self.preview_line_ids.filtered(lambda line: line.status == 'duplicate')),
            'error_count': 0,
            'imported_total': total,
            'import_log': _(
                'Imported %(count)s transactions (total %(total)s). Skipped %(skipped)s duplicate(s).',
                count=len(ready), total=total,
                skipped=len(self.preview_line_ids.filtered(lambda line: line.status == 'duplicate')),
            ),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bank.statement.csv.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        self.ensure_one()
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=self.delimiter or ',')
        writer.writerow(TEMPLATE_COLUMNS)
        writer.writerow([datetime.date.today().strftime(self.date_format or '%Y-%m-%d'),
                          'Sample transaction label', '1000.00', 'Sample Partner', 'REF-0001'])
        content = buffer.getvalue().encode('utf-8-sig')
        attachment = self.env['ir.attachment'].create({
            'name': 'bank_statement_import_template.csv', 'type': 'binary',
            'datas': base64.b64encode(content), 'mimetype': 'text/csv',
            'res_model': self._name, 'res_id': self.id,
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%s?download=true' % attachment.id, 'target': 'self'}

    def action_download_template_xlsx(self):
        self.ensure_one()
        if openpyxl is None:
            raise UserError(_('openpyxl is not available on this server - cannot generate the XLSX file.'))
        bold = Font(bold=True)
        header_fill = PatternFill('solid', fgColor='D9E1F2')
        warn_fill = PatternFill('solid', fgColor='FFF2CC')
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Instructions'
        rows = [
            ('Feature', 'Bank Statement CSV/XLSX Import'),
            ('Required columns', 'date, label, amount'),
            ('Optional columns', 'partner_name, reference'),
            ('Date format', 'Must match the wizard selected format: %s' % (self.date_format or 'YYYY-MM-DD')),
            ('Amount', 'Signed decimal - positive for money in, negative for money out.'),
            ('Duplicates', 'Duplicate rows are shown in preview and skipped when enabled.'),
            ('IMPORTANT', 'Fill the Bank Transactions sheet and remove the example row before upload.'),
        ]
        for row_number, (label, value) in enumerate(rows, start=1):
            cell = ws.cell(row=row_number, column=1, value=label)
            cell.font = bold
            ws.cell(row=row_number, column=2, value=value)
            if label == 'IMPORTANT':
                ws.cell(row=row_number, column=1).fill = warn_fill
                ws.cell(row=row_number, column=2).fill = warn_fill
        ws.column_dimensions['A'].width = 22
        ws.column_dimensions['B'].width = 90
        ws2 = wb.create_sheet('Bank Transactions')
        for col, header in enumerate(TEMPLATE_COLUMNS, start=1):
            cell = ws2.cell(row=1, column=col, value=header)
            cell.font = bold
            cell.fill = header_fill
        ws2.append([datetime.date.today().strftime(self.date_format or '%Y-%m-%d'),
                    'Sample transaction label', 1000.00, 'Sample Partner', 'REF-0001'])
        ws2.cell(row=2, column=1).font = Font(italic=True)
        ws2['A3'] = '(delete this example row before importing)'
        for col in range(1, len(TEMPLATE_COLUMNS) + 1):
            ws2.column_dimensions[chr(64 + col)].width = 22
        buffer = io.BytesIO()
        wb.save(buffer)
        attachment = self.env['ir.attachment'].create({
            'name': 'bank_statement_import_template.xlsx', 'type': 'binary',
            'datas': base64.b64encode(buffer.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name, 'res_id': self.id,
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%s?download=true' % attachment.id, 'target': 'self'}

    def action_view_imported(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Imported Transactions'),
            'res_model': 'account.bank.statement.line', 'view_mode': 'list,form',
            'domain': [('journal_id', '=', self.journal_id.id)],
            'context': {'search_default_journal_id': self.journal_id.id},
        }


class BankStatementCsvImportLine(models.TransientModel):
    _name = 'bank.statement.csv.import.line'
    _description = 'Bank Statement Import Preview Line'
    _order = 'row_number'

    wizard_id = fields.Many2one('bank.statement.csv.import.wizard', required=True, ondelete='cascade')
    row_number = fields.Integer(string='File Row', readonly=True)
    date = fields.Date(readonly=True)
    label = fields.Char(readonly=True)
    amount = fields.Float(readonly=True)
    partner_name = fields.Char(readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    reference = fields.Char(readonly=True)
    status = fields.Selection([
        ('ready', 'Ready'), ('duplicate', 'Duplicate'), ('error', 'Error'),
    ], readonly=True)
    error_message = fields.Text(readonly=True)
