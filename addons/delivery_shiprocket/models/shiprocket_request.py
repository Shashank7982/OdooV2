# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import requests

from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

BASE_URL = 'https://apiv2.shiprocket.in/v1/external'
TIMEOUT = 30


class ShiprocketRequest:
    """ Thin wrapper around the Shiprocket REST API (apiv2.shiprocket.in). """

    def __init__(self, email, password, token=None):
        self.email = email
        self.password = password
        self.token = token

    # -------------------------------------------------------------------
    # Auth
    # -------------------------------------------------------------------
    def authenticate(self):
        response = self._call('POST', '/auth/login', {
            'email': self.email,
            'password': self.password,
        }, authenticated=False)
        self.token = response.get('token')
        return self.token

    # -------------------------------------------------------------------
    # Serviceability / rate check
    # -------------------------------------------------------------------
    def check_serviceability(self, pickup_pincode, delivery_pincode, weight, cod, declared_value=None):
        params = {
            'pickup_postcode': pickup_pincode,
            'delivery_postcode': delivery_pincode,
            'weight': weight,
            'cod': 1 if cod else 0,
        }
        if declared_value:
            params['declared_value'] = declared_value
        return self._call('GET', '/courier/serviceability', params)

    # -------------------------------------------------------------------
    # Orders / shipments
    # -------------------------------------------------------------------
    def create_order(self, order_vals):
        return self._call('POST', '/orders/create/adhoc', order_vals)

    def assign_awb(self, shipment_id, courier_id=None):
        payload = {'shipment_id': shipment_id}
        if courier_id:
            payload['courier_id'] = courier_id
        return self._call('POST', '/courier/assign/awb', payload)

    def generate_label(self, shipment_ids):
        return self._call('POST', '/courier/generate/label', {'shipment_id': shipment_ids})

    def generate_manifest(self, shipment_ids):
        return self._call('POST', '/manifests/generate', {'shipment_id': shipment_ids})

    def request_pickup(self, shipment_ids):
        return self._call('POST', '/courier/generate/pickup', {'shipment_id': shipment_ids})

    def track_by_awb(self, awb_code):
        return self._call('GET', f'/courier/track/awb/{awb_code}')

    def track_by_shipment(self, shipment_id):
        return self._call('GET', f'/courier/track/shipment/{shipment_id}')

    def cancel_order(self, order_ids):
        return self._call('POST', '/orders/cancel', {'ids': order_ids})

    def cancel_shipment(self, awb_codes):
        return self._call('POST', '/orders/cancel/shipment/awbs', {'awbs': awb_codes})

    def download_file(self, url):
        """ Download a binary resource (label/manifest PDF) from an absolute URL
        returned by the Shiprocket API. """
        if not self.token:
            self.authenticate()
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not download the file from Shiprocket: %s", e))
        return response.content

    # -------------------------------------------------------------------
    # Internal HTTP helper
    # -------------------------------------------------------------------
    def _call(self, method, endpoint, payload=None, authenticated=True):
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            if not self.token:
                self.authenticate()
            headers['Authorization'] = f'Bearer {self.token}'

        url = f'{BASE_URL}{endpoint}'
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=TIMEOUT)
            else:
                response = requests.request(method, url, json=payload, headers=headers, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not reach the Shiprocket API: %s", e))

        # Token expired -> re-authenticate once and retry.
        if response.status_code == 401 and authenticated:
            self.token = None
            self.authenticate()
            headers['Authorization'] = f'Bearer {self.token}'
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=TIMEOUT)
            else:
                response = requests.request(method, url, json=payload, headers=headers, timeout=TIMEOUT)

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400:
            message = data.get('message') or data.get('errors') or response.text
            _logger.warning('Shiprocket API error [%s %s]: %s', method, endpoint, message)
            raise UserError(_("Shiprocket error: %s", message))

        return data
