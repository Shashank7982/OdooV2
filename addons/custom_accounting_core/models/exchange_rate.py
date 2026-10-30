"""ExchangeRate-API integration for Odoo's native currency rate engine."""

import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    is_manual = fields.Boolean(
        string="Manual Override",
        default=False,
        help="This rate is maintained manually and is not overwritten by the API updater.",
    )


class ResCurrency(models.Model):
    _inherit = "res.currency"

    @api.model
    def _exchange_rate_api_key(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param("custom_accounting.exchange_rate_api_key")
            or os.environ.get("EXCHANGERATE_API_KEY")
        )

    @api.model
    def _fetch_exchange_rates(self, base_currency):
        api_key = self._exchange_rate_api_key()
        if not api_key:
            raise UserError(_("Configure the ExchangeRate-API key in Accounting Settings first."))

        url = "https://v6.exchangerate-api.com/v6/%s/latest/%s" % (
            api_key.strip(), base_currency.name.upper()
        )
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "Odoo"})
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            _logger.exception("ExchangeRate-API request failed")
            raise UserError(_("Could not retrieve exchange rates: %s") % error) from error

        if payload.get("result") != "success":
            raise UserError(
                _("ExchangeRate-API returned an error: %s")
                % payload.get("error-type", _("unknown error"))
            )
        return payload.get("conversion_rates", {})

    @api.model
    def _update_rates_from_exchange_api(self, raise_if_unconfigured=True):
        """Fetch rates once per company and write them to Odoo's rate table.

        ExchangeRate-API returns ``1 BASE = quote TARGET``. Odoo stores the
        reciprocal for a target currency, because its rate is expressed as
        ``1 TARGET = rate COMPANY_CURRENCY``.
        """
        if not self._exchange_rate_api_key():
            message = _("ExchangeRate-API key is not configured; skipping scheduled update.")
            if raise_if_unconfigured:
                raise UserError(message)
            _logger.warning(message)
            return 0

        companies = self.env["res.company"].sudo().search([]).mapped("root_id")
        today = fields.Date.context_today(self)
        updated = 0
        for company in companies:
            base = company.currency_id
            rate_company = company.root_id
            rates = self._fetch_exchange_rates(base)
            for currency in self.sudo().with_context(active_test=False).search([]):
                if currency == base:
                    stored_rate = 1.0
                else:
                    manual_rate = self.env["res.currency.rate"].sudo().search([
                        ("currency_id", "=", currency.id),
                        ("company_id", "=", rate_company.id),
                        ("is_manual", "=", True),
                    ], order="name desc", limit=1)
                    if manual_rate:
                        _logger.info("Keeping manual exchange rate for %s", currency.name)
                        continue
                    quote = rates.get(currency.name.upper())
                    if not quote:
                        _logger.warning("No exchange rate returned for %s", currency.name)
                        continue
                    stored_rate = 1.0 / float(quote)

                rate = self.env["res.currency.rate"].sudo().search([
                    ("currency_id", "=", currency.id),
                    ("company_id", "=", rate_company.id),
                    ("name", "=", today),
                ], limit=1)
                values = {"rate": stored_rate, "name": today, "company_id": rate_company.id}
                if rate:
                    rate.write(values)
                else:
                    values["currency_id"] = currency.id
                    self.env["res.currency.rate"].sudo().create(values)
                updated += 1

        self.env["ir.config_parameter"].sudo().set_param(
            "custom_accounting.exchange_rate_last_update", fields.Datetime.now()
        )
        _logger.info("Updated %s currency rates from ExchangeRate-API", updated)
        return updated


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    exchange_rate_api_key = fields.Char(
        string="ExchangeRate-API Key",
        config_parameter="custom_accounting.exchange_rate_api_key",
        help="Stored as an Odoo system parameter and never committed to source control.",
    )
    exchange_rate_last_update = fields.Char(
        string="Last Successful Update", compute="_compute_exchange_rate_last_update",
        readonly=True,
    )
    manual_exchange_rate_currency_id = fields.Many2one(
        "res.currency",
        string="Manual Rate Currency",
        domain="[('active', '=', True)]",
        default=lambda self: self.env.ref("base.USD", raise_if_not_found=False),
        help="Currency whose rate should be maintained manually when the API is unavailable.",
    )
    manual_exchange_rate_value = fields.Float(
        string="Manual Exchange Rate",
        digits=(16, 6),
        help="Enter how much company currency equals 1 unit of the selected currency. Example: 1 USD = 83 INR, enter 83 when the company currency is INR.",
    )
    manual_exchange_rate_date = fields.Date(
        string="Manual Rate Date",
        default=fields.Date.context_today,
    )



    def _compute_exchange_rate_last_update(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "custom_accounting.exchange_rate_last_update", default="Never"
        )
        for record in self:
            record.exchange_rate_last_update = value

    def action_update_exchange_rates(self):
        self.ensure_one()
        self.env["ir.config_parameter"].sudo().set_param(
            "custom_accounting.exchange_rate_api_key", self.exchange_rate_api_key or ""
        )
        self.env["res.currency"]._update_rates_from_exchange_api()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_test_exchange_rate_connection(self):
        self.ensure_one()
        self.env["ir.config_parameter"].sudo().set_param(
            "custom_accounting.exchange_rate_api_key", self.exchange_rate_api_key or ""
        )
        base_currency = self.env.company.currency_id
        rates = self.env["res.currency"]._fetch_exchange_rates(base_currency)
        if not rates or base_currency.name.upper() not in rates:
            raise UserError(
                _("The API responded, but no rates were returned for %s.") % base_currency.name
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Successful"),
                "message": _("ExchangeRate-API is connected. Rates for %s were received.")
                % base_currency.name,
                "type": "success",
                "sticky": False,
            },
        }

    def action_set_manual_exchange_rate(self):
        self.ensure_one()
        currency = self.manual_exchange_rate_currency_id
        value = self.manual_exchange_rate_value
        if not currency or value <= 0:
            raise UserError(_("Select a currency and enter a manual exchange rate greater than zero."))

        company = self.env.company.root_id
        stored_rate = 1.0 if currency == company.currency_id else 1.0 / value
        Rate = self.env["res.currency.rate"].sudo()
        rate = Rate.search([
            ("currency_id", "=", currency.id),
            ("company_id", "=", company.id),
            ("name", "=", self.manual_exchange_rate_date),
        ], limit=1)
        values = {
            "rate": stored_rate,
            "name": self.manual_exchange_rate_date,
            "company_id": company.id,
            "is_manual": True,
        }
        if rate:
            rate.write(values)
        else:
            Rate.create(dict(values, currency_id=currency.id))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Manual Rate Saved"),
                "message": _("Manual rate saved for 1 %s = %s company currency.") % (currency.name, value),
                "type": "success",
                "sticky": False,
            },
        }

    def action_clear_manual_exchange_rate(self):
        self.ensure_one()
        if not self.manual_exchange_rate_currency_id:
            raise UserError(_("Select a currency first."))
        self.env["res.currency.rate"].sudo().search([
            ("currency_id", "=", self.manual_exchange_rate_currency_id.id),
            ("company_id", "=", self.env.company.root_id.id),
            ("is_manual", "=", True),
        ]).unlink()
        return {"type": "ir.actions.client", "tag": "reload"}


