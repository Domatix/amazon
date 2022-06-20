from odoo import models, fields
from dateutil.parser import parse
from datetime import datetime, timedelta
from sp_api.base import Marketplaces
from sp_api.api import Orders
from sp_api.api import Sellers
from sp_api.util import throttle_retry, load_all_pages
import time
from dateutil import parser
import pytz
utc = pytz.utc


class AmazonSeller(models.Model):
    _inherit = 'amazon.seller'

    api_mode = fields.Selection(
        [('mws', 'MWS'),
         ('sp', 'SP')],
        default='sp',
        string='Api')

    role_arn = fields.Char(
        string='Role ARN')

    refresh_token = fields.Char(
        string='Refresh token')

    lwa_app_id = fields.Char(
        string='LWA Client ID')

    lwa_client_secret = fields.Char(
        string='LWA Client Secret')

    def connect_sp_api(self, country_id):
        credentials = dict(refresh_token=self.refresh_token,
                           lwa_app_id=self.lwa_app_id,
                           lwa_client_secret=self.lwa_client_secret,
                           aws_access_key=self.access_key,
                           aws_secret_key=self.secret_key,
                           role_arn=self.role_arn,
                           )
        # TO-DO every country
        if country_id.code == 'ES':
            country_code = Marketplaces.ES

        return credentials, country_code

    def get_marketplaces(self):
        if self.api_mode == 'sp':
            credentials, country_code = self.connect_sp_api(self.country_id)
            marketplaces = Sellers(credentials=credentials, marketplace=country_code).get_marketplace_participation()
            marketplace_obj = self.env['amazon.marketplace']
            pricelist_obj = self.env['product.pricelist']
            lang_obj = self.env['res.lang']
            country_obj = self.env['res.country']
            for market in marketplaces.payload:
                if market.get('participation').get('isParticipating'):
                    marketplace_id = market.get('marketplace').get('id')
                    country_code = market.get('marketplace').get('countryCode')
                    name = market.get('marketplace').get('name')
                    lang_code = market.get('marketplace').get('defaultLanguageCode')
                    currency_code = market.get('marketplace').get('defaultCurrencyCode')
                    pricelist_id = pricelist_obj.search([
                        ('currency_id.name', '=', currency_code)])
                    lang_id = lang_obj.search([('code', '=', lang_code)])
                    country_id = country_obj.search([('code', '=', country_code)])

                    vals = {
                        'seller_id': self.id,
                        'name': name,
                        'market_code': marketplace_id,
                        'pricelist_id': pricelist_id and pricelist_id[0].id or
                        False,
                        'lang_id': lang_id and lang_id[0].id or False,
                        'country_id': country_id and country_id[0].id or
                        self.country_id and self.country_id.id or False,
                        'company_id': self.company_id.id,
                    }
                    marketplace_rec = marketplace_obj.search(
                        [('seller_id', '=', self.id),
                         ('market_code', '=', marketplace_id)])
                    if marketplace_rec:
                        marketplace_rec.write(vals)
                    else:
                        marketplace_obj.create(vals)

                else:
                    continue

        else:
            res = super().get_marketplaces()
            return res

    # Create FBM and FBA orders
    def action_import_orders(self):
        self.import_orders()

    def import_orders(self, marketplaces=False, seller=False,
                      last_import_date=False, single_market=False):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super().import_orders(marketplaces, seller, last_import_date, single_market)
            return res

    def import_order_manual(self, marketplaces, seller, start_date, end_date):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super().import_order_manual(marketplaces, seller, start_date, end_date)
            return res

    def _create_sale_order(self, order, marketplace, mws_obj):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super()._create_sale_order(order, marketplace, mws_obj)
            return res

    def _get_partner(self, order):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super()._get_partner(order)
            return res

    def _create_sale_order_lines(self, amazon_order_ref, marketplace,
                                 mws_obj):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super()._create_sale_order_lines(amazon_order_ref, marketplace, mws_obj)
            return res

    def get_product(self, sku):
        return self.env['product.product'].search([('default_code', '=', sku)],
                                                  limit=1)

    def get_item_values(self, item, product, order_line_vals, marketplace):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super().get_item_values(item, product, order_line_vals, marketplace)
            return res

    def get_shipping_values(self, item, shipment_product_id,
                            order_line_vals, marketplace):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super().get_shipping_values(item, shipment_product_id, order_line_vals, marketplace)
            return res

    def get_gift_values(self, item, gift_product_id,
                        order_line_vals, marketplace):
        if self.api_mode == 'sp':
            # to-do
            print('to-do')
        else:
            res = super().get_gift_values(item, gift_product_id, order_line_vals, marketplace)
            return res
