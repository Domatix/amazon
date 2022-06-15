from odoo import fields, models


class name(models.TransientModel):
    _name = 'amazon.import.manual'

    def _default_marketplaces(self):
        marketplaces = self.env['amazon.marketplace'].browse(
            self.env.context.get('active_ids'))
        return marketplaces

    start_date = fields.Datetime(
        string='Start date')

    end_date = fields.Datetime(
        string='End date')

    marketplace_ids = fields.Many2many(
        comodel_name='amazon.marketplace',
        string='Marketplaces',
        default=_default_marketplaces)

    def import_orders(self):
        seller = self.env['amazon.marketplace'].search([]).mapped('seller_id')
        seller.import_order_manual(
            self.marketplace_ids, seller, self.start_date, self.end_date)
