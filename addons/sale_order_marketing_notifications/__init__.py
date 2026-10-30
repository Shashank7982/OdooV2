from . import models


def post_init_hook(env):
    """Point the order-confirmation and payment-followup mail templates at the
    existing marketing SMTP relay (identified by 'brevo' in its host), so these
    customer notifications go out through that dedicated server instead of the
    default transactional one."""
    marketing_server = env['ir.mail_server'].search([('smtp_host', 'ilike', 'brevo')], limit=1)
    if not marketing_server:
        return

    for xmlid in (
        # 'sale.mail_template_sale_confirmation' is the one actually used by
        # action_confirm()/_get_confirmation_template() on auto-send; the older
        # 'sale.email_template_edi_sale' is only used by the manual "Send by
        # Email" quotation wizard. Both are set so both paths route consistently.
        'sale.mail_template_sale_confirmation',
        'sale.email_template_edi_sale',
        'custom_accounting_followup.mail_template_followup_reminder',
    ):
        template = env.ref(xmlid, raise_if_not_found=False)
        if template and not template.mail_server_id:
            template.mail_server_id = marketing_server.id
