from odoo import models, fields
from dateutil.parser import parse
from datetime import datetime, timedelta
from sp_api.base import Marketplaces
from sp_api.api import Orders
from sp_api.api import Sellers
from sp_api.api import Tokens
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

    @throttle_retry()
    @load_all_pages()
    def load_all_orders(self, **kwargs):
        """
        a generator function to return all pages, obtained by NextToken
        """
        credentials, country_code = self.connect_sp_api(self.country_id)
        # token_res = Tokens(credentials=credentials, marketplace=country_code).create_restricted_data_token(restrictedResources=[{
        #          "method": "GET",
        #          "path": "/orders/v0/orders",
        #          "dataElements": ["buyerInfo", "shippingAddress"]
        #          }
        # ])
        # return Orders(restricted_data_token=token_res.payload['restrictedDataToken'],credentials=credentials, marketplace=country_code).get_orders(**kwargs)
        return Orders(credentials=credentials, marketplace=country_code).get_orders(**kwargs)

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
            if not seller:
                seller = self.env['amazon.seller'].search([], limit=1)
            if not marketplaces:
                marketplaces = seller.marketplace_ids
            if not last_import_date:
                last_import_date = seller.last_import_date_seller.isoformat(
                    sep='T')
            else:
                last_import_date = last_import_date.isoformat(sep='T')

            values = {'LastUpdatedAfter': last_import_date,
                      'OrderStatuses': ['Unshipped', 'PartiallyShipped', 'Shipped'],
                      # 'RestrictedResources': ['buyerInfo', 'shippingAddress'],
                      }
            orders_data = []
            market_obj = self.env['amazon.marketplace']
            marketplaceids = marketplaces.mapped('market_code')
            for page in self.load_all_orders(**values):
                for order in page.payload.get('Orders'):
                    market_code = order.get('MarketplaceId')
                    marketplace = market_obj.search([
                        ('market_code', '=', market_code)])
                    sale_channel = order.get('SalesChannel')
                    seller._create_sale_order(order, marketplace, page)
                    # Date to synchronize every time an order is imported
                    last_purchase_date = order.get('PurchaseDate')
                    last_purchase_date = parse(last_purchase_date).replace(tzinfo=None)
                    if single_market:
                        marketplace.last_import_date = last_purchase_date
                    else:
                        seller.last_import_date_seller = last_purchase_date
                        marketplace.last_import_date = last_purchase_date
            # commit a batch of 100 orders due to request throttled from Amazon
            self.env.cr.commit()
        else:
            res = super().import_orders(marketplaces, seller, last_import_date, single_market)
            return res

    def import_order_manual(self, marketplaces, seller, start_date, end_date):
        if self.api_mode == 'sp':
            start_date = start_date.isoformat(sep='T')
            end_date = end_date.isoformat(sep='T')
            market_obj = self.env['amazon.marketplace']
            marketplaceids = marketplaces.mapped('market_code')
            values = {'LastUpdatedAfter': start_date,
                      'LastUpdatedBefore': end_date,
                      'OrderStatuses': ['Unshipped', 'PartiallyShipped', 'Shipped'],
                      'MarketplaceIds': marketplaceids,
                      # 'RestrictedResources': ['buyerInfo', 'shippingAddress'],
                      }
            for page in self.load_all_orders(**values):
                for order in page.payload.get('Orders'):
                    market_code = order.get('MarketplaceId')
                    marketplace = market_obj.search([
                        ('market_code', '=', market_code)])
                    sale_channel = order.get('SalesChannel')
                    seller._create_sale_order(order, marketplace, page)
            # commit a batch of 100 orders due to request throttled from Amazon
            self.env.cr.commit()
        else:
            res = super().import_order_manual(marketplaces, seller, start_date, end_date)
            return res

    def _create_sale_order(self, order, marketplace, page):
        if self.api_mode == 'sp':
            sale_obj = self.env['sale.order']
            amazon_order_ref = order.get('AmazonOrderId')
            order_found = sale_obj.search([
                ('amazon_reference', '=', amazon_order_ref)])
            if not order_found:
                invoice_partner, delivery_partner = self._get_partner(order)
                ord_lines = self._create_sale_order_lines(
                    amazon_order_ref, marketplace, order)
                vals = self.get_order_vals(order, ord_lines, amazon_order_ref, marketplace, invoice_partner, delivery_partner)
                order = sale_obj.create(vals)
        else:
            res = super()._create_sale_order(order, marketplace, page)
            return res

    def get_order_vals(self, order, ord_lines, amazon_order_ref, marketplace, invoice_partner, delivery_partner):
        fulfillment_channel = order.get('FulfillmentChannel')
        amazon_fulfillment = 'fba' if fulfillment_channel == 'AFN' else 'fbm'
        date_order = parser.parse(
            order.get('PurchaseDate')).replace(tzinfo=None)
        pricelist = marketplace.pricelist_id
        user_id = marketplace.user_id
        team_id = marketplace.team_id
        vals = {
            'origin': amazon_order_ref,
            'date_order': date_order,
            'partner_id': invoice_partner.id,
            'partner_shipping_id': delivery_partner.id,
            'pricelist_id': pricelist.id,
            'user_id': user_id.id,
            'team_id': team_id.id,
            'order_line': [(0, 0, order_line) for order_line in ord_lines],
            'fiscal_position_id': marketplace.fiscal_position_id.id,
            'amazon_reference': amazon_order_ref,
            'amazon_fulfillment': amazon_fulfillment,
            'company_id': self.company_id.id,
            'amazon_marketplace_id': marketplace.id,
            'payment_term_id': marketplace.payment_term_id.id,
            }
        return vals

    def _get_partner(self, order):
        if self.api_mode == 'sp':
            partner_obj = self.env['res.partner']
            country_obj = self.env['res.country']
            lang_obj = self.env['res.lang']
            state_obj = self.env['res.country.state']
            shipping_address = order.get('ShippingAddress', {})
            buyer_info = order.get('BuyerInfo', {})
            country_code = shipping_address.get('CountryCode', False)
            country = country_obj.search([('code', '=', country_code)], limit=1)
            lang = False
            if country_code:
                country_code_lower = country_code.lower()
                lang = lang_obj.search([('iso_code', '=', country_code_lower)])
            state_code = shipping_address.get(
                'StateOrRegion')
            state = state_obj.search([
                ('country_id', '=', country.id), '|',
                ('code', '=', state_code),
                ('name', '=', state_code)],
                limit=1)
            # if not state and country and state_code:
            #     state = state_obj.create({
            #         'country_id': country.id,
            #         'name': state_code,
            #         'code': state_code
            #     })
            email = buyer_info.get('BuyerEmail', False)
            street = shipping_address.get('AddressLine1', False)
            street2 = shipping_address.get('AddressLine2', False)
            postalcode = shipping_address.get('PostalCode', False)
            deliv_name = shipping_address.get('Name', email)
            phone = shipping_address.get('Phone', False)
            city = shipping_address.get('City', False)
            invoice_name = buyer_info.get('BuyerName', email)
            domain = []
            street and domain.append(('street', '=', street))
            street2 and domain.append(('street2', '=', street2))
            email and domain.append(('email', '=', email))
            phone and domain.append(('phone', '=', phone))
            city and domain.append(('city', '=', city))
            postalcode and domain.append(('zip', '=', postalcode))
            state and domain.append(('state_id', '=', state.id))
            country and domain.append(('country_id', '=', country.id))
            deliv_name and domain.append(('name', '=', deliv_name))
            domain.append(('type', '=', 'delivery'))
            delivery_vals = {
                'name': deliv_name,
                'is_company': False,
                'street': street,
                'street2': street2,
                'city': city,
                'country_id': country.id,
                'type': 'delivery',
                'phone': phone,
                'zip': postalcode,
                'state_id': state.id,
                'email': email,
                'lang': lang.code,
                'company_id': self.company_id.id
            }
            delivery_partner = partner_obj.search(domain, limit=1)
            if not delivery_partner:
                delivery_partner = partner_obj.create(delivery_vals)
                delivery_partner._onchange_zip_id()
            domain.remove(('name', '=', deliv_name))
            domain.append(('name', '=', invoice_name))
            domain.remove(('type', '=', 'delivery'))
            domain.append(('type', '=', 'invoice'))
            invoice_partner = partner_obj.search(domain, limit=1)
            if not invoice_partner:
                if email:
                    invoice_partner = partner_obj.search([
                        ('email', '=', email),
                        ('type', '=', 'invoice')],
                        limit=1)
                if phone and not invoice_partner:
                    invoice_partner = partner_obj.search([
                        ('phone', '=', phone),
                        ('type', '=', 'invoice')],
                        limit=1)
                if not invoice_partner:
                    invoice_partner_vals = {
                        'name': invoice_name,
                        'is_company': False,
                        'street': street,
                        'street2': street2,
                        'city': city,
                        'country_id': country.id,
                        'type': 'invoice',
                        'phone': phone,
                        'zip': postalcode,
                        'state_id': state.id,
                        'email': email,
                        'lang': lang.code,
                        'company_id': self.env.user.company_id.id
                    }
                    invoice_partner = partner_obj.create(invoice_partner_vals)
                    invoice_partner._onchange_zip_id()
            delivery_partner.parent_id = invoice_partner.id
            return invoice_partner, delivery_partner
        else:
            res = super()._get_partner(order)
            return res

    def _create_sale_order_lines(self, amazon_order_ref, market,
                                 order):
        if self.api_mode == 'sp':
            product_obj = self.env['product.product']
            shipment_product_id = self.env.ref('amazon_integration.amazon_shipping_product')
            gift_product_id = self.env.ref('amazon_integration.amazon_gift_product')
            not_found_product_id = self.env.ref('amazon_integration.amazon_not_found_product')
            order_line_vals = []
            credentials, country_code = self.connect_sp_api(self.country_id)
            lines = Orders(credentials=credentials, marketplace=country_code).get_order_items(amazon_order_ref)
            for item in lines.payload.get('OrderItems'):
                sku = item.get('SellerSKU')
                product = self.get_product(sku)
                if not product:
                    product = not_found_product_id
                # Order Lines
                order_line_vals = self.get_item_values(
                    item, product, order_line_vals, market)
                shipping = item.get('ShippingPrice', {}).get('Amount')
                # gift = item.get('GiftWrapPrice')
                if shipping:
                    order_line_vals = self.get_shipping_values(
                        item, shipment_product_id, order_line_vals,
                        market)
                # if gift:
                #     order_line_vals = self.get_gift_values(
                #         item, gift_product_id, order_line_vals,
                #         market)
            return order_line_vals

        else:
            res = super()._create_sale_order_lines(amazon_order_ref, marketplace, order)
            return res

    def get_product(self, sku):
        return self.env['product.product'].search([('default_code', '=', sku)],
                                                  limit=1)

    def get_item_values(self, item, product, order_line_vals, marketplace):
        if self.api_mode == 'sp':
            quantity = float(item.get('QuantityOrdered'))
            item_price = float(item.get('ItemPrice').get('Amount'))
            description = item.get('Title')
            fiscal_position = marketplace.fiscal_position_id
            product_tax = product.taxes_id.filtered(
                lambda x: x.company_id.id == self.company_id.id)
            tax = fiscal_position.map_tax(product_tax)
            tax_reduce = tax.amount / 100 + 1
            item_price = item_price / tax_reduce
            promotion_discount = float(
                item.get('PromotionDiscount').get('Amount'))
            if promotion_discount:
                promotion_discount = promotion_discount / tax_reduce
            amazon_order_item_id = item.get('OrderItemId')
            item_vals = {
                'product_id': product.id,
                'product_uom_qty': quantity,
                'name': description,
                'tax_id': [(6, 0, tax.ids)],
                'price_unit': item_price,
                'discount': (promotion_discount / item_price) * 100,
                'amazon_order_item_id': amazon_order_item_id,
            }
            order_line_vals.append(item_vals)
            return order_line_vals
        else:
            res = super().get_item_values(item, product, order_line_vals, marketplace)
            return res

    def get_shipping_values(self, item, shipment_product_id,
                            order_line_vals, marketplace):
        if self.api_mode == 'sp':
            fiscal_position = marketplace.fiscal_position_id
            product_tax = shipment_product_id.taxes_id.filtered(
                lambda x: x.company_id.id == self.company_id.id)
            tax = fiscal_position.map_tax(product_tax)
            tax_reduce = tax.amount / 100 + 1
            shipping_price = float(
                item.get('ShippingPrice').get('Amount'))
            shipping_price = shipping_price / tax_reduce
            shipping_discount = float(
                item.get('ShippingDiscount').get('Amount'))
            if shipping_discount:
                shipping_discount = shipping_discount / tax_reduce
            item_shipping_vals = {
                'product_id': shipment_product_id.id,
                'product_uom_qty': 1,
                'tax_id': [(6, 0, tax.ids)],
                'price_unit': shipping_price,
                'discount': (shipping_discount / shipping_price) * 100,
            }
            order_line_vals.append(item_shipping_vals)
            return order_line_vals
        else:
            res = super().get_shipping_values(item, shipment_product_id, order_line_vals, marketplace)
            return res

    # def get_gift_values(self, item, gift_product_id,
    #                     order_line_vals, marketplace):
    #     if self.api_mode == 'sp':
    #         # to-do
    #         print('to-do')
    #     else:
    #         res = super().get_gift_values(item, gift_product_id, order_line_vals, marketplace)
    #         return res
