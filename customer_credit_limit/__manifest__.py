# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Customer Credit limit',
    'version': '1.0',
    'category': 'Sale',
    'summary': 'Customer Credit Limit',
    'description': """
    While confirming sale order, check customer's credit limit and decide if customer's order can be confirmed or need approval.
    """,
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'https://www.synconics.com',
    'depends': ['sale_management'],
    'data': [
        "security/res_groups.xml",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/res_partner_view.xml",
        "views/sale_view.xml",
        "views/update_credit_view.xml",
        "security/ir.model.access.csv"
    ],
    'images': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
