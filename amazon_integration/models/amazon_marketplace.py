from odoo import models, fields
from datetime import datetime


class AmazonMarketplace(models.Model):
    _name = 'amazon.marketplace'
    _description = 'Amazon Markets from a seller'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        track_visibility='onchange')

    market_code = fields.Char(
        string='Marketplace ID',
        track_visibility='onchange')

    color = fields.Integer(
        string='Color Index')

    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country')

    lang_id = fields.Many2one(
        comodel_name='res.lang',
        string='Language')

    seller_id = fields.Many2one(
        comodel_name='amazon.seller',
        string='Seller')

    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Pricelist')

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company')

    last_import_date = fields.Datetime(
        string='Last Import Date',
        default=datetime.now())

    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string='Fiscal Position')

    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment Term')

    team_id = fields.Many2one(
        comodel_name='crm.team',
        string='Sale Team')

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Commercial')

    order_count = fields.Integer(
        string='Order #',
        compute='_compute_order_count')


    def _compute_order_count(self):
        for record in self:
            orders = self.env['sale.order'].search([('amazon_marketplace_id','=', record.id)])
            record.order_count = len(orders)

    # Import FBM and FBA orders

    def import_market_orders(self):
        self.seller_id.import_orders(marketplaces=self,
                                     seller=self.seller_id,
                                     last_import_date=self.last_import_date,
                                     single_market=True)
    def action_view_sale_order(self):
        action = self.env.ref('sale.action_orders').read()[0]
        action['context'] = {
            'search_default_amazon_marketplace_id': self.id,
            'default_amazon_marketplace_id': self.id,
        }
        return action
