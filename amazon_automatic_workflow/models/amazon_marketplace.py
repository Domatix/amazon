from odoo import models, fields


class AmazonMarketplace(models.Model):
    _inherit = 'amazon.marketplace'

    workflow_process_id = fields.Many2one(
        comodel_name='sale.workflow.process',
        string='Workflow process')
