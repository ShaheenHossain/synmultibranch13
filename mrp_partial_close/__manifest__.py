# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'MRP Partial Close',
    'version': '1.0',
    'category': 'MRP',
    'summary': 'MRP Partial Close',
    'description': """
        This module allow to close the MO before producing all quantity.
    """,
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'http://www.synconics.com',
    'depends': ['mrp_extended'],
    'data': [
        'views/mrp_production_views.xml',
        'wizard/mrp_partial_close_confirmation_view.xml',
        'report/mrp_production_templates.xml',
    ],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
