# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import requests

from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

PRODUCTION_BASE_URL = 'https://my.ithinklogistics.com/api_v3'
STAGING_BASE_URL = 'https://pre-alpha.ithinklogistics.com/api_v3'
TRACK_BASE_URL = 'https://api.ithinklogistics.com/api_v3'
TIMEOUT = 30


class IThinkRequest:
    """ Thin wrapper around the iThink Logistics REST API (api_v3). """

    def __init__(self, access_token, secret_key, test_mode=False):
        self.access_token = access_token
        self.secret_key = secret_key
        self.test_mode = test_mode

    def _base_url(self, track=False):
        if self.test_mode:
            return STAGING_BASE_URL
        return TRACK_BASE_URL if track else PRODUCTION_BASE_URL

    # -------------------------------------------------------------------
    # Serviceability / rate check
    # -------------------------------------------------------------------
    def check_pincode(self, pincode):
        return self._call('/pincode/check.json', {'pincode': pincode})

    def get_rate(self, from_pincode, to_pincode, weight_kg, length_cm, width_cm, height_cm,
                 payment_method='prepaid', product_mrp=0.0, order_type='forward'):
        return self._call('/rate/check.json', {
            'from_pincode': from_pincode,
            'to_pincode': to_pincode,
            'shipping_length_cms': length_cm,
            'shipping_width_cms': width_cm,
            'shipping_height_cms': height_cm,
            'shipping_weight_kg': weight_kg,
            'order_type': order_type,
            'payment_method': payment_method,
            'product_mrp': product_mrp,
        })

    # -------------------------------------------------------------------
    # Orders / shipments
    # -------------------------------------------------------------------
    def add_order(self, shipment_vals, pickup_address_id, logistics=''):
        payload = {
            'shipments': [shipment_vals],
            'pickup_address_id': pickup_address_id,
            'logistics': logistics,
            's_type': 'ground',
            'order_type': '',
        }
        return self._call('/order/add.json', payload)

    def cancel_order(self, awb_numbers):
        return self._call('/order/cancel.json', {
            'awb_numbers': ','.join(awb_numbers) if isinstance(awb_numbers, (list, tuple)) else awb_numbers,
        })

    def track_order(self, awb_numbers):
        return self._call('/order/track.json', {
            'awb_number_list': ','.join(awb_numbers) if isinstance(awb_numbers, (list, tuple)) else awb_numbers,
        }, track=True)

    def print_label(self, awb_numbers, page_size='A4'):
        return self._call('/shipping/label.json', {
            'awb_numbers': ','.join(awb_numbers) if isinstance(awb_numbers, (list, tuple)) else awb_numbers,
            'page_size': page_size,
        })

    def print_manifest(self, awb_numbers):
        return self._call('/shipping/manifest.json', {
            'awb_numbers': ','.join(awb_numbers) if isinstance(awb_numbers, (list, tuple)) else awb_numbers,
        })

    def download_file(self, url):
        """ Download a binary resource (label/manifest PDF) from an absolute URL
        returned by the iThink Logistics API. """
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not download the file from iThink Logistics: %s", e))
        return response.content

    # -------------------------------------------------------------------
    # Internal HTTP helper
    # -------------------------------------------------------------------
    def _call(self, endpoint, data, track=False):
        if not self.access_token or not self.secret_key:
            raise UserError(_("Please configure your iThink Logistics Access Token and Secret Key."))

        data = dict(data)
        data['access_token'] = self.access_token
        data['secret_key'] = self.secret_key

        url = f'{self._base_url(track=track)}{endpoint}'
        try:
            response = requests.post(url, json={'data': data}, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not reach the iThink Logistics API: %s", e))

        try:
            result = response.json()
        except ValueError:
            result = {}

        if response.status_code >= 400 or result.get('status') == 'error':
            message = result.get('html_message') or result.get('message') or response.text
            _logger.warning('iThink Logistics API error [%s]: %s', endpoint, message)
            raise UserError(_("iThink Logistics error: %s", message))

        return result
