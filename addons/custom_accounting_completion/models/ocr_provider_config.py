import base64
import json
import mimetypes
import urllib.request

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.custom_accounting_ocr.models.ocr_provider import PROVIDER_REGISTRY


class AccountOcrProviderConfig(models.Model):
    _name = 'account.ocr.provider.config'
    _description = 'OCR Provider Configuration'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    endpoint_url = fields.Char(string='HTTP JSON Endpoint', required=True)
    api_key = fields.Char(string='API Key', groups='base.group_system')
    timeout = fields.Integer(default=30, help='HTTP timeout in seconds.')
    max_file_size_mb = fields.Integer(default=10, string='Maximum File Size (MB)')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.constrains('endpoint_url', 'timeout', 'max_file_size_mb')
    def _check_configuration(self):
        for config in self:
            if not config.endpoint_url.startswith(('http://', 'https://')):
                raise ValidationError(_('The OCR endpoint must start with http:// or https://.'))
            if config.timeout <= 0 or config.max_file_size_mb <= 0:
                raise ValidationError(_('OCR timeout and maximum file size must be positive.'))


class AccountBillDigitization(models.Model):
    _inherit = 'account.bill.digitization'

    provider = fields.Selection(
        selection=lambda self: [(key, provider.label) for key, provider in PROVIDER_REGISTRY.items()]
        + [('http_json', 'HTTP JSON OCR')],
        default='manual', required=True,
    )
    provider_config_id = fields.Many2one(
        'account.ocr.provider.config', string='Provider Configuration',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
    )

    def _validate_document(self):
        self.ensure_one()
        if not self.document:
            raise UserError(_('Attach a document first.'))
        filename = (self.document_filename or '').lower()
        extension = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        if extension not in ('pdf', 'jpg', 'jpeg', 'png'):
            raise ValidationError(_('Only PDF, JPG, JPEG, and PNG vendor bills are supported.'))
        limit_mb = self.provider_config_id.max_file_size_mb if self.provider_config_id else 10
        if len(base64.b64decode(self.document)) > limit_mb * 1024 * 1024:
            raise ValidationError(_('The uploaded vendor bill exceeds the %s MB limit.') % limit_mb)

    def _http_json_extract(self):
        self.ensure_one()
        config = self.provider_config_id
        if not config:
            raise ValidationError(_('Select an OCR provider configuration for HTTP JSON OCR.'))
        raw = base64.b64decode(self.document)
        mimetype = mimetypes.guess_type(self.document_filename or '')[0] or 'application/octet-stream'
        payload = json.dumps({
            'filename': self.document_filename or self.name,
            'mimetype': mimetype,
            'content_base64': base64.b64encode(raw).decode(),
        }).encode()
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if config.api_key:
            headers['Authorization'] = 'Bearer %s' % config.api_key
        request = urllib.request.Request(config.endpoint_url, data=payload, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(request, timeout=config.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
        except Exception as error:
            raise UserError(_('OCR provider request failed: %s') % error) from error
        return result.get('data', result) if isinstance(result, dict) else {}

    def action_run_extraction(self):
        for record in self:
            record._validate_document()
            if record.provider != 'http_json':
                super(AccountBillDigitization, record).action_run_extraction()
                continue
            extracted = record._http_json_extract()
            vals = {'state': 'extracted'}
            if extracted.get('vendor_name'):
                partner = self.env['res.partner'].search([('name', 'ilike', extracted['vendor_name'])], limit=1)
                if partner:
                    vals['partner_id'] = partner.id
            for key in ('invoice_number', 'invoice_date', 'due_date', 'tax_amount', 'total_amount'):
                if extracted.get(key) is not None:
                    vals[key] = extracted[key]
            record.write(vals)
            record.message_post(body=_('HTTP JSON OCR extraction completed. Review the values before confirmation.'))
