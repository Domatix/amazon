# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Amazon Selling Partner Integration',
    'summary': """
        Amazon SP-API Integration""",
    'version': '13.0.1.0.0',
    'license': 'AGPL-3',
    'website': 'https://github.com/OCA/connector-ecommerce',
    'depends': ['amazon_integration'],
    'category': 'Sales',
    'author': 'Domatix, '
              'Odoo Community Association (OCA)',
    'external_dependencies': {
        'python': [
            'python-amazon-sp-api',
        ],
    },
    'data': ['views/amazon_seller.xml'],
    'development_status': 'Alpha',
    'installable': True,
}
