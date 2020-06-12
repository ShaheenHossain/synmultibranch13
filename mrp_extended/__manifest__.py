# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'MRP Extention',
    'version': '1.3',
    'category': 'MRP',
    'summary': 'MRP Extention',
    'description': """
    This module will add reprocessing workorder in manufacturing process.
    """,
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'http://www.synconics.com',
    'depends': ['quality_mrp_workorder'],
    'data': [
        'security/ir.model.access.csv',
        'security/mrp_security.xml',
        'data/mrp_workorder_data.xml',
        'views/mrp_team_view.xml',
        'views/quality_views.xml',
        'views/mrp_workcenter_view.xml',
        'wizard/mrp_workorder_import_excel_xls_view.xml',
        'wizard/mrp_workorder_rework_confirmation_views.xml',
        'wizard/mrp_workorder_unbuild_confirmation_view.xml',
        'views/mrp_workorder_view.xml',
        'views/res_config_settings_views.xml',
        'views/stock_production_lot_view.xml'
    ],
    'images': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
