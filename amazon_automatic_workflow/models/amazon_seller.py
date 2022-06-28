from odoo import models, fields


class AmazonSeller(models.Model):
    _inherit = 'amazon.seller'

    def get_order_vals(self, order, ord_lines, amazon_order_ref, marketplace, invoice_partner, delivery_partner):
        res = super().get_order_vals(order, ord_lines, amazon_order_ref, marketplace, invoice_partner, delivery_partner)
        res['workflow_process_id'] = marketplace.workflow_process_id.id 
        return res
