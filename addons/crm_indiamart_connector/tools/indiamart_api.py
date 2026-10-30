import logging

import requests

_logger = logging.getLogger(__name__)

PULL_API_URL = 'https://mapi.indiamart.com/wservce/crm/crmListing/v2/'
DATETIME_FORMAT = '%d-%b-%Y%H:%M:%S'


class IndiamartAPIError(Exception):
    """Raised when Indiamart's Pull API returns a non-success response."""


def fetch_leads(crm_key, start_datetime, end_datetime, timeout=30):
    """Fetch Indiamart Lead Manager inquiries in [start_datetime, end_datetime].

    Indiamart caps each call to a 3-day window and expects local (IST) time
    in DD-MMM-YYYYHH:MI:SS format. Returns a list of raw lead dicts.
    """
    params = {
        'glusr_crm_key': crm_key,
        'start_time': start_datetime.strftime(DATETIME_FORMAT),
        'end_time': end_datetime.strftime(DATETIME_FORMAT),
    }
    response = requests.get(PULL_API_URL, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    code = payload.get('CODE')
    if code not in (200, '200'):
        message = payload.get('MESSAGE') or payload
        raise IndiamartAPIError(f'Indiamart API error (CODE={code}): {message}')

    leads = payload.get('RESPONSE') or []
    _logger.info('Indiamart Pull API returned %d lead(s)', len(leads))
    return leads
