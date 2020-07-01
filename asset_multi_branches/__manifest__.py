# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Asset Multi Branches',
    'version': '1.0',
    'summary': 'Application provides functionality of manage multi branches for companies.',
    'sequence': 30,
    'description': """
    """,
    'category': 'Asset',
    'license': 'OPL-1',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'www.synconics.com',
    'depends': ['account_asset', 'multi_branches'],
    'data': [
        'views/account_asset_view.xml',
        ],
    'demo': [],
    'qweb': [],
    'images': [],
    'price': 0.0,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': False,
}
