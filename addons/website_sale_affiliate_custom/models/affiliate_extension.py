from odoo import models, fields, api


class SaleAffiliateExtension(models.Model):
    _inherit = 'sale.affiliate'

    affiliate_url = fields.Char(
        string='Affiliate Link (Path)',
        compute='_compute_affiliate_url',
        help='Direct affiliate link: /affiliate/<key>?redirect=/',
    )
    affiliate_param_url = fields.Char(
        string='Affiliate Link (Query Param)',
        compute='_compute_affiliate_url',
        help='Query parameter affiliate link: /?aff_ref=<key>',
    )

    # Additional fields for the extended affiliate program
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        default=10.0,
        help='Default commission percentage on confirmed sales.',
    )
    discount_rate = fields.Float(
        string='Customer Discount Rate (%)',
        default=10.0,
        help='Discount percentage given to customers using this affiliate link/coupon.',
    )
    is_active = fields.Boolean(string='Active', default=True)
    user_id = fields.Many2one(
        'res.users', string='Portal User',
        help='Portal user linked to this affiliate for self-service access.',
    )
    total_clicks = fields.Integer(
        string='Total Clicks', compute='_compute_totals', store=True,
    )
    total_commission = fields.Monetary(
        string='Total Commission', compute='_compute_totals', store=True,
    )
    pending_commission = fields.Monetary(
        string='Pending Commission', compute='_compute_totals', store=True,
    )
    paid_commission = fields.Monetary(
        string='Paid Commission', compute='_compute_totals', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    coupon_program_id = fields.Many2one(
        'loyalty.program', string='Coupon Program',
        help='Loyalty program used to generate affiliate coupons.',
    )

    click_ids = fields.One2many('affiliate.click', 'affiliate_id', string='Clicks')
    commission_ids = fields.One2many('affiliate.commission', 'affiliate_id', string='Commissions')
    withdrawal_ids = fields.One2many('affiliate.withdrawal', 'affiliate_id', string='Withdrawals')

    @api.depends('key')
    def _compute_affiliate_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        for rec in self:
            if rec.key:
                rec.affiliate_url = '%s/affiliate/%s?redirect=/' % (base_url, rec.key)
                rec.affiliate_param_url = '%s/shop?aff_ref=%s' % (base_url, rec.key)
            else:
                rec.affiliate_url = False
                rec.affiliate_param_url = False

    @api.depends('click_ids', 'commission_ids', 'commission_ids.state', 'commission_ids.amount',
                 'withdrawal_ids', 'withdrawal_ids.state')
    def _compute_totals(self):
        for rec in self:
            rec.total_clicks = len(rec.click_ids)
            commissions = rec.commission_ids.filtered(lambda c: c.state == 'confirmed')
            rec.total_commission = sum(commissions.mapped('amount'))
            rec.paid_commission = sum(
                rec.withdrawal_ids.filtered(lambda w: w.state == 'paid').mapped('amount')
            )
            rec.pending_commission = rec.total_commission - rec.paid_commission

    def action_generate_coupon(self):
        """Generate a loyalty coupon for this affiliate's partner."""
        self.ensure_one()
        if not self.coupon_program_id:
            return
        self.env['loyalty.card'].sudo().create({
            'program_id': self.coupon_program_id.id,
            'partner_id': self.partner_id.id,
            'code': self.key,
            'points': 1,
        })
