# Odoo 18 Project Tech Stack

This document details the complete technology stack used in this Odoo 18 project.

---

## 1. Core Platform & Architecture
* **Core Application Framework:** [Odoo](https://www.odoo.com) version 18.0 (LGPL-3).
* **Programming Language:** Python 3.10+ (typically running Python 3.12+ on modern systems).
* **Database Management System:** PostgreSQL (configured in `odoo.conf` via `psycopg2`).
* **Concurrency Model:** Multi-threaded/event-driven via `gevent` and `greenlet` (for POS and live chat features).

---

## 2. Backend & Framework Dependencies
Key library integrations configured in the project's dependencies (`setup.py` / `requirements.txt`):

* **Web Framework & Server:** Werkzeug (WSGI utility library) & Jinja2 (templating engine).
* **Security & Cryptography:** `cryptography`, `passlib` (password hashing), `pyopenssl`, `asn1crypto`.
* **XML/HTML Parsing & Sanitization:** `lxml` and `lxml-html-clean`.
* **Networking & Protocols:** `requests` and `urllib3` (HTTP client), `zeep` (SOAP client).
* **Serialization & Formats:** `cbor2` (CBOR serialization), `ofxparse` (financial OFX documents), `vobject` (iCalendar/vCard parser).
* **Reporting & PDFs:** `reportlab` (PDF generation), `PyPDF2` (PDF manipulation).
* **System Operations:** `psutil` (process/system monitoring), `pyserial` and `pyusb` (hardware connectivity for IoT/POS).

---

## 3. Frontend & Styling
* **Web UI Framework:** Odoo Web Client (OWL Framework - Odoo Widget Library).
* **CSS & Stylesheets:** Vanilla CSS & Sass compilation utilizing the `libsass` module.
* **JS Minification:** `rjsmin` for compilation/assets bundle optimization.
* **QR Codes & Imaging:** `qrcode`, `pillow` (PIL fork for image processing).

---

## 4. Payment Integrations
* **Stripe Integration:** Localized `payment_stripe` core addon with customized controllers and views located in `addons/payment_stripe_custom` utilizing Python's `stripe` library.
* **Additional Providers:** Built-in support for Adyen, PayPal, Authorize.net, Mercado Pago, Mollie, and Razorpay.

---

## 5. Development & Utilities
* **Local Server Configuration:** Managed via `odoo.conf` in the project root.
* **Localization:** `Babel` (i18n support) and `pytz` (Timezones).
* **Unit Testing:** `freezegun` (time mocking) and Odoo standard testing framework modules.
