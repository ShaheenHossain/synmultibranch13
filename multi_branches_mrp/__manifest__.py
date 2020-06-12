# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Multiple Branch(Unit) Operations for Manufacturing',
    'version': '1.0',
    'summary': 'Application provide functionality of manage Multiple Branch management for companies in Manufacturing process.',
    'sequence': 30,
    'description': """
        This application provide functionality of manage Multiple Branch management for companies in Manufacturing process.
    """,
    'category': 'Manufacturing',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'www.synconics.com',
    'depends': ['multi_branches', 'mrp'],
    'data': [
        'security/mrp_branch_security.xml',
        'security/ir.model.access.csv',
        'views/multi_branches_mrp_view.xml'
        ],
    'demo': [],
    'images': ['static/description/main_screen.png'],
    'price': 40.0,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1'
}
