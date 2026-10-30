import base64
import io
from datetime import date

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
except ImportError:  # pragma: no cover - openpyxl ships with Odoo's requirements
    openpyxl = None

TEMPLATE_VERSION = '1.0'

# Generic "what to enter" phrasing per Odoo field type - not feature-specific
# invention, just plain-language translation of the field's own type/relation.
TYPE_GUIDANCE = {
    'char': 'Free text.',
    'text': 'Free text (can be multiple lines).',
    'boolean': 'Enter TRUE or FALSE (Yes/No).',
    'integer': 'Whole number.',
    'float': 'Decimal number.',
    'monetary': 'Decimal amount in the record\'s currency.',
    'date': 'Date in YYYY-MM-DD format.',
    'datetime': 'Date and time in YYYY-MM-DD HH:MM:SS format.',
    'selection': 'Pick one value from the "Allowed Values" sheet.',
    'many2one': 'Enter the exact Name of an existing record in Odoo (see "Allowed Values" sheet for how it is matched).',
    'many2many': 'Multiple existing records - managed as a list inside Odoo, not a single value.',
    'one2many': 'A list of related records - managed as a sub-list inside Odoo, not a single value.',
    'binary': 'A file upload (document/image) - not a text value.',
    'html': 'Rich text.',
}

# Reasonable, generic "documents an admin usually needs on hand" per feature
# group - not model-specific invention, just standard bookkeeping practice.
REQUIRED_DOCUMENTS_BY_GROUP = {
    'gst_partner': ['GST certificate / GSTIN', 'PAN card', 'CIN (if company)', 'Cancelled cheque or bank proof', 'FSSAI license (if a food business)'],
    'invoice': ['Sales order / quotation reference', 'Delivery/shipping details', 'Applicable tax rates'],
    'vendor_bill': ['Vendor\'s original invoice/bill document', 'Vendor GSTIN/PAN', 'Purchase order reference (if any)'],
    'payment': ['Bank statement or payment advice', 'Cheque/UTR/transaction reference'],
    'bank_journal': ['Bank account statement or passbook', 'IFSC/SWIFT details', 'Cancelled cheque'],
    'asset': ['Purchase invoice for the asset', 'Vendor bill it was created from (if any)'],
    'budget': ['Approved budget figures from management/finance'],
    'deferred': ['Underlying invoice/bill being deferred', 'Recognition schedule agreed with accountant'],
    'followup': ['Aging/overdue report', 'Collections policy'],
    'affiliate': ['Affiliate\'s bank/payout details', 'Commission calculation basis'],
    'company': ['Company PAN/CIN/GST registration certificate', 'Bank details for UPI/QR', 'Authorized signatory signature image'],
    'other': [],
}


class AccountFieldGuide(models.Model):
    _name = 'account.field.guide'
    _description = 'Downloadable Field Guide / Data Template Registry'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    key = fields.Char(required=True, copy=False, help='Stable technical key, e.g. "res_partner_gst".')
    sequence = fields.Integer(default=10)
    guide_type = fields.Selection([
        ('field_guide', 'Admin Field Guide (form-only feature, not importable)'),
        ('data_template', 'Importable Data Template (real upload/import exists)'),
    ], required=True, default='field_guide')
    feature_group = fields.Selection([
        ('gst_partner', 'GST / Partner Master Data'),
        ('invoice', 'Customer Invoice'),
        ('vendor_bill', 'Vendor Bill'),
        ('payment', 'Payments'),
        ('bank_journal', 'Bank / Cash Journal'),
        ('asset', 'Fixed Assets'),
        ('budget', 'Budgets'),
        ('deferred', 'Deferred Revenue/Expense'),
        ('followup', 'Customer Follow-up'),
        ('affiliate', 'Affiliate Payouts'),
        ('company', 'Company / GST / Branding Settings'),
        ('other', 'Other'),
    ], required=True, default='other')
    model_name = fields.Char(required=True, help='Technical model name, e.g. res.partner')
    menu_path = fields.Char(help='Where to find this screen in Odoo, e.g. Accounting > Customers > Customers')
    field_names = fields.Text(
        required=True,
        help='One technical field name per line, in the order they should appear on the form.')
    notes = fields.Text(help='Extra notes shown on the Instructions sheet (optional).')
    active = fields.Boolean(default=True)

    def _get_model_or_raise(self):
        self.ensure_one()
        if self.model_name not in self.env:
            raise UserError(_(
                'This guide targets model "%(model)s", which is not available - the module that '
                'provides it may not be installed.', model=self.model_name,
            ))
        return self.env[self.model_name]

    def action_download(self):
        self.ensure_one()
        if openpyxl is None:
            raise UserError(_('openpyxl is not available on this server - cannot generate the XLSX file.'))
        Model = self._get_model_or_raise()
        fields_get = Model.fields_get()
        field_list = [f.strip() for f in (self.field_names or '').splitlines() if f.strip()]
        missing = [f for f in field_list if f not in fields_get]
        if missing:
            raise UserError(_(
                'These fields no longer exist on %(model)s (the module may have changed): %(fields)s',
                model=self.model_name, fields=', '.join(missing),
            ))

        content = self._build_workbook(fields_get, field_list)
        filename = '%s_field_guide.xlsx' % (self.key or self.model_name.replace('.', '_'))
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _build_workbook(self, fields_get, field_list):
        self.ensure_one()
        wb = openpyxl.Workbook()
        bold = Font(bold=True)
        header_fill = PatternFill('solid', fgColor='D9E1F2')
        warn_fill = PatternFill('solid', fgColor='FFF2CC')

        # --- Instructions ---
        ws = wb.active
        ws.title = 'Instructions'
        is_template = self.guide_type == 'data_template'
        rows = [
            ('Feature', self.name),
            ('Menu path', self.menu_path or '-'),
            ('Odoo model', self.model_name),
            ('Template version', TEMPLATE_VERSION),
            ('Generated on', str(date.today())),
            ('', ''),
            ('IMPORTANT',
             'This is an importable data template - fill it and upload it back through the '
             'matching Import/Upload screen.' if is_template else
             'REFERENCE TEMPLATE - NOT FOR UPLOAD. This lists the fields shown on the Odoo '
             'screen so you can collect the information in advance. Enter the values directly '
             'into Odoo; this file is not read by any importer.'),
        ]
        if self.notes:
            rows.append(('Notes', self.notes))
        for r, (label, value) in enumerate(rows, start=1):
            c1 = ws.cell(row=r, column=1, value=label)
            c1.font = bold
            ws.cell(row=r, column=2, value=value)
            if label == 'IMPORTANT':
                ws.cell(row=r, column=1).fill = warn_fill
                ws.cell(row=r, column=2).fill = warn_fill
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 90

        # --- Fields to Fill ---
        ws2 = wb.create_sheet('Fields to Fill')
        headers = ['Field Label', 'Technical Name', 'Required', 'Type', 'What to Enter',
                    'Example', 'Value to be Entered']
        for col, h in enumerate(headers, start=1):
            cell = ws2.cell(row=1, column=col, value=h)
            cell.font = bold
            cell.fill = header_fill
        row_idx = 2
        allowed_values_rows = []
        for fname in field_list:
            fdef = fields_get[fname]
            ftype = fdef.get('type')
            guidance = TYPE_GUIDANCE.get(ftype, 'See Odoo screen for details.')
            if fdef.get('help'):
                guidance = '%s %s' % (fdef['help'].strip(), guidance)
            example = self._example_for(fdef)
            ws2.cell(row=row_idx, column=1, value=fdef.get('string', fname))
            ws2.cell(row=row_idx, column=2, value=fname)
            ws2.cell(row=row_idx, column=3, value='Yes' if fdef.get('required') else 'No')
            ws2.cell(row=row_idx, column=4, value=ftype)
            ws2.cell(row=row_idx, column=5, value=guidance)
            ws2.cell(row=row_idx, column=6, value=example)
            row_idx += 1

            if ftype == 'selection' and fdef.get('selection'):
                for value, label in fdef['selection']:
                    allowed_values_rows.append((fdef.get('string', fname), str(value), str(label)))
            elif ftype == 'many2one' and fdef.get('relation'):
                allowed_values_rows.append((
                    fdef.get('string', fname), '(relation)',
                    'Must match the Name of an existing "%s" record in Odoo.' % fdef['relation']))
        for col, width in enumerate([28, 22, 10, 12, 55, 25, 25], start=1):
            ws2.column_dimensions[chr(64 + col)].width = width

        # --- Allowed Values ---
        ws3 = wb.create_sheet('Allowed Values')
        for col, h in enumerate(['Field', 'Value', 'Label / Match Rule'], start=1):
            cell = ws3.cell(row=1, column=col, value=h)
            cell.font = bold
            cell.fill = header_fill
        for r, (field_label, value, label) in enumerate(allowed_values_rows, start=2):
            ws3.cell(row=r, column=1, value=field_label)
            ws3.cell(row=r, column=2, value=value)
            ws3.cell(row=r, column=3, value=label)
        for col, width in enumerate([28, 20, 55], start=1):
            ws3.column_dimensions[chr(64 + col)].width = width

        # --- Example ---
        ws4 = wb.create_sheet('Example')
        for col, fname in enumerate(field_list, start=1):
            fdef = fields_get[fname]
            ws4.cell(row=1, column=col, value=fdef.get('string', fname)).font = bold
            ws4.cell(row=2, column=col, value=self._example_for(fdef))
        ws4.cell(row=3, column=1, value='(example row - delete before using this as a working sheet)').font = Font(italic=True)

        # --- Required Documents ---
        ws5 = wb.create_sheet('Required Documents')
        ws5.cell(row=1, column=1, value='Typically needed before filling this in').font = bold
        for r, doc in enumerate(REQUIRED_DOCUMENTS_BY_GROUP.get(self.feature_group, []), start=2):
            ws5.cell(row=r, column=1, value=doc)
        ws5.column_dimensions['A'].width = 60

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def _example_for(self, fdef):
        ftype = fdef.get('type')
        if ftype == 'selection' and fdef.get('selection'):
            return fdef['selection'][0][1]
        if ftype == 'many2one':
            return 'Existing %s name' % (fdef.get('relation') or 'record')
        if ftype == 'boolean':
            return 'TRUE'
        if ftype == 'date':
            return str(date.today())
        if ftype == 'monetary' or ftype == 'float':
            return '1000.00'
        if ftype == 'integer':
            return '1'
        return 'Sample text'
