import base64
import io

from odoo import _, fields, models
from odoo.exceptions import UserError

from .ocr_provider import PROVIDER_REGISTRY, get_provider

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover
    canvas = None


class AccountBillDigitization(models.Model):
    _name = 'account.bill.digitization'
    _description = 'Vendor Bill Digitization (OCR)'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(default='New Digitization', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    document = fields.Binary(string='Bill Document (PDF/Image)', required=True)
    document_filename = fields.Char()
    provider = fields.Selection(
        selection=lambda self: [(k, v.label) for k, v in PROVIDER_REGISTRY.items()],
        default='manual', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('extracted', 'Extracted / Awaiting Review'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Bill Created'),
    ], default='draft', tracking=True)

    partner_id = fields.Many2one('res.partner', string='Vendor')
    invoice_number = fields.Char()
    invoice_date = fields.Date()
    due_date = fields.Date()
    tax_amount = fields.Monetary(currency_field='currency_id')
    total_amount = fields.Monetary(currency_field='currency_id')

    duplicate_warning = fields.Char(compute='_compute_duplicate_warning')
    vendor_bill_id = fields.Many2one('account.move', readonly=True, copy=False)

    def _compute_duplicate_warning(self):
        for record in self:
            record.duplicate_warning = False
            if record.partner_id and record.invoice_number:
                existing = self.env['account.move'].search([
                    ('move_type', '=', 'in_invoice'),
                    ('partner_id', '=', record.partner_id.id),
                    ('ref', '=', record.invoice_number),
                    ('id', '!=', record.vendor_bill_id.id if record.vendor_bill_id else 0),
                ], limit=1)
                if existing:
                    record.duplicate_warning = _(
                        "Possible duplicate: vendor bill %(name)s already has this reference.",
                        name=existing.name,
                    )

    def action_download_preparation_guide(self):
        """Download a sample bill layout and field guide PDF."""
        if canvas is None:
            raise UserError(_('reportlab is not available on this server - cannot generate the PDF guide.'))

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 2 * cm

        def line(text, size=10, bold=False, gap=0.6 * cm):
            nonlocal y
            c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
            c.drawString(2 * cm, y, text)
            y -= gap

        line('SAMPLE - DO NOT POST', 16, True)
        line('Vendor Bill Preparation Guide', 13, True)
        line('')
        line('This page shows the fields the Vendor Bill Digitization screen', 10)
        line('(Accounting > Vendor Bill Digitization) will ask you to review.', 10)
        line('')
        line('Workflow: 1) Attach the bill (PDF or image)  2) Run Extraction', 10, True)
        line('3) Review/correct the fields below  4) Confirm  5) Create Vendor Bill', 10, True)
        line('')
        line('Fields to check on your vendor\'s bill before uploading:', 11, True)
        for field_line in [
            '- Vendor name (must match an existing Odoo vendor, or be created)',
            '- Vendor invoice number',
            '- Invoice date',
            '- Due date (if stated on the bill)',
            '- Tax amount',
            '- Total amount',
        ]:
            line(field_line, 10)
        line('')
        line('File format: PDF, JPG, JPEG, or PNG up to the configured size limit.', 10, True)
        line('A clear photo/scan of the full bill is recommended for', 10)
        line('readability. Only one document is stored per digitization record;', 10)
        line('for a multi-page bill, upload a single multi-page PDF.', 10)
        line('')
        line('Duplicate check: a possible duplicate is flagged if the same', 10, True)
        line('vendor + invoice number already exists as a vendor bill.', 10)
        line('')
        line('The original document is kept as an attachment on the vendor', 10, True)
        line('bill once created, for audit reference.', 10)
        c.showPage()
        c.save()
        content = buffer.getvalue()

        attachment = self.env['ir.attachment'].create({
            'name': 'vendor_bill_preparation_guide_SAMPLE.pdf',
            'type': 'binary',
            'datas': base64.b64encode(content),
            'mimetype': 'application/pdf',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_run_extraction(self):
        for record in self:
            if not record.document:
                raise UserError(_("Attach a document first."))
            provider = get_provider(record.provider)
            file_bytes = base64.b64decode(record.document)
            extracted = provider.extract(file_bytes, 'application/octet-stream', record.document_filename)

            vals = {'state': 'extracted'}
            if extracted.get('vendor_name'):
                partner = self.env['res.partner'].search([('name', 'ilike', extracted['vendor_name'])], limit=1)
                if partner:
                    vals['partner_id'] = partner.id
            for key in ('invoice_number', 'invoice_date', 'due_date', 'tax_amount', 'total_amount'):
                if extracted.get(key):
                    vals[key] = extracted[key]
            record.write(vals)
            if record.provider == 'manual':
                record.message_post(body=_(
                    "No OCR provider configured — please fill in the fields manually below, then confirm."))

    def action_confirm(self):
        for record in self:
            if not record.partner_id or not record.total_amount:
                raise UserError(_("Vendor and Total Amount are required before confirming."))
            record.state = 'confirmed'

    def action_create_vendor_bill(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_("Confirm the extracted data before creating the vendor bill."))
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'company_id': record.company_id.id,
                'partner_id': record.partner_id.id,
                'ref': record.invoice_number,
                'invoice_date': record.invoice_date,
                'invoice_date_due': record.due_date,
                'invoice_line_ids': [(0, 0, {
                    'name': _('Digitized bill - %s', record.invoice_number or record.name),
                    'quantity': 1,
                    'price_unit': record.total_amount - record.tax_amount,
                })],
            })
            if record.document:
                self.env['ir.attachment'].create({
                    'name': record.document_filename or _('Original Document'),
                    'type': 'binary',
                    'datas': record.document,
                    'res_model': 'account.move',
                    'res_id': move.id,
                })
            record.write({'state': 'posted', 'vendor_bill_id': move.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self[-1].vendor_bill_id.id,
        }
