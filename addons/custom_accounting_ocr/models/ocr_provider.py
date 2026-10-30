"""
Pluggable OCR provider architecture for vendor bill digitization.

To add a real OCR service later: subclass OcrProviderBase, implement
extract(), and register it in PROVIDER_REGISTRY. No paid service is
hard-coded here — ManualOcrProvider is the only built-in provider and
performs no extraction.
"""


class OcrProviderBase:
    """ Base interface every OCR provider must implement. """

    key = 'base'
    label = 'Base Provider'

    def extract(self, file_bytes, mimetype, filename=None):
        """ Must return a dict with any subset of the keys:
        vendor_name, invoice_number, invoice_date, due_date,
        tax_amount, total_amount, lines (list of dicts).
        Must never raise on unrecognized documents — return {} instead. """
        raise NotImplementedError


class ManualOcrProvider(OcrProviderBase):
    """ No-op provider: user types in all fields themselves after attaching
    the document. This is the default/only built-in provider. """

    key = 'manual'
    label = 'Manual (No Provider)'

    def extract(self, file_bytes, mimetype, filename=None):
        return {}


PROVIDER_REGISTRY = {
    'manual': ManualOcrProvider,
}


def get_provider(key):
    provider_class = PROVIDER_REGISTRY.get(key, ManualOcrProvider)
    return provider_class()
