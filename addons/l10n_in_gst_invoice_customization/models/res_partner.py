from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Legal entity types requiring CIN + TAN unconditionally (registered companies).
# All other business types (Partnership, LLP, Proprietorship, Cooperative Society,
# NGO, Trust, Government, Other) leave CIN optional - no ROC company registration.
BUSINESS_TYPE_REQUIRING_CIN_TAN = ('private_limited', 'public_limited')
BUSINESS_TYPE_REQUIRING_FSSAI = ('restaurant', 'cloud_kitchen', 'food_manufacturing', 'food_catering', 'food_retail_grocery')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # GSTIN = vat, PAN = l10n_in_pan (both already provided by l10n_in)
    gst_cin = fields.Char(string='CIN Number')
    gst_iec = fields.Char(string='IEC Code')
    gst_tan = fields.Char(string='TAN Number')
    gst_tan_applicable = fields.Boolean(
        string='Registered for TAN (Tax Deduction/Collection)',
        help="Tick if this entity deducts/collects tax at source and therefore needs a TAN, "
             "even though its business type doesn't require one automatically.")
    gst_fssai = fields.Char(string='FSSAI Number')

    gst_contact_person = fields.Char(string='Contact Person Name')
    gst_contact_number = fields.Char(string='Contact Person Number')

    business_type = fields.Selection([
        ('private_limited', 'Private Limited Company'),
        ('public_limited', 'Public Limited Company'),
        ('partnership', 'Partnership'),
        ('llp', 'Limited Liability Partnership'),
        ('proprietorship', 'Proprietorship'),
        ('cooperative_society', 'Cooperative Society'),
        ('ngo', 'NGO'),
        ('trust', 'Trust'),
        ('government', 'Government Organization'),
        ('other', 'Other'),
    ], string='Business Type')
    business_type_other = fields.Char(string='Business Type (Other)')
    gst_is_food_business = fields.Boolean(string='Food / Beverage Business')

    # Business Type is required for a company only in the UI (view-level
    # `required="is_company"` on the field) - deliberately not a Python
    # @api.constrains, since that would retroactively block writes to every
    # pre-existing company contact in the database that predates this field
    # (delivery carriers, banks, other addons' partners, etc.) the moment
    # anything else on them is edited.

    @api.constrains('business_type', 'gst_cin', 'gst_tan', 'gst_tan_applicable', 'gst_is_food_business', 'gst_fssai')
    def _check_gst_conditional_mandatory_fields(self):
        for partner in self:
            if partner.business_type in BUSINESS_TYPE_REQUIRING_CIN_TAN and not (partner.gst_cin and partner.gst_tan):
                raise ValidationError(_(
                    "CIN Number and TAN Number are mandatory for a Private Limited or "
                    "Public Limited Company."
                ))
            if (partner.business_type not in BUSINESS_TYPE_REQUIRING_CIN_TAN
                    and partner.gst_tan_applicable and not partner.gst_tan):
                raise ValidationError(_(
                    "TAN Number is mandatory once this entity is marked as registered for "
                    "tax deduction/collection."
                ))
            if (partner.gst_is_food_business or partner.business_type in BUSINESS_TYPE_REQUIRING_FSSAI) and not partner.gst_fssai:
                raise ValidationError(_(
                    "FSSAI Number is mandatory for a food/beverage business."
                ))
