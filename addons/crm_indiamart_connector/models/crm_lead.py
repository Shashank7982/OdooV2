import logging
from datetime import timedelta

import requests

from odoo import api, fields, models

from ..tools.indiamart_api import IndiamartAPIError, fetch_leads

_logger = logging.getLogger(__name__)

# Indiamart's Pull API expects local IST timestamps, while Odoo stores
# datetimes in UTC internally.
IST_OFFSET = timedelta(hours=5, minutes=30)
# Indiamart caps each Pull API call to a 3-day window.
MAX_PULL_WINDOW = timedelta(days=3)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    indiamart_unique_query_id = fields.Char(
        string='Indiamart Query ID', copy=False, index=True,
        help='Indiamart\'s UNIQUE_QUERY_ID, used to avoid re-importing the same inquiry.',
    )

    _sql_constraints = [
        (
            'indiamart_unique_query_id_uniq',
            'unique(indiamart_unique_query_id)',
            'This Indiamart inquiry has already been imported.',
        ),
    ]

    @api.model
    def _cron_fetch_indiamart_leads(self):
        companies = self.env['res.company'].sudo().search([
            ('indiamart_enabled', '=', True),
            ('indiamart_crm_key', '!=', False),
        ])
        for company in companies:
            self._fetch_indiamart_leads_for_company(company)

    @api.model
    def _fetch_indiamart_leads_for_company(self, company):
        now_utc = fields.Datetime.now()
        start_utc = company.indiamart_last_pull or (now_utc - timedelta(hours=1))
        end_utc = min(now_utc, start_utc + MAX_PULL_WINDOW)
        if start_utc >= end_utc:
            return

        try:
            raw_leads = fetch_leads(
                company.indiamart_crm_key,
                start_utc + IST_OFFSET,
                end_utc + IST_OFFSET,
            )
        except (IndiamartAPIError, requests.RequestException):
            _logger.exception(
                'Indiamart lead fetch failed for company %s', company.display_name)
            return

        for raw_lead in raw_leads:
            self._create_lead_from_indiamart(raw_lead, company)

        company.sudo().write({'indiamart_last_pull': end_utc})

    @api.model
    def _create_lead_from_indiamart(self, raw_lead, company):
        unique_id = raw_lead.get('UNIQUE_QUERY_ID')
        if not unique_id:
            return
        if self.sudo().search_count([('indiamart_unique_query_id', '=', unique_id)]):
            return

        source = self.env.ref(
            'crm_indiamart_connector.utm_source_indiamart', raise_if_not_found=False)
        vals = {
            'name': raw_lead.get('QUERY_PRODUCT_NAME') or 'Indiamart Inquiry',
            'contact_name': raw_lead.get('SENDER_NAME'),
            'partner_name': raw_lead.get('SENDER_COMPANY'),
            'phone': raw_lead.get('SENDER_MOBILE'),
            'email_from': raw_lead.get('SENDER_EMAIL'),
            'street': raw_lead.get('SENDER_ADDRESS'),
            'city': raw_lead.get('SENDER_CITY'),
            'zip': raw_lead.get('SENDER_PINCODE'),
            'description': raw_lead.get('QUERY_MESSAGE'),
            'indiamart_unique_query_id': unique_id,
            'company_id': company.id,
            'type': 'lead',
        }
        if source:
            vals['source_id'] = source.id
        self.sudo().create(vals)
