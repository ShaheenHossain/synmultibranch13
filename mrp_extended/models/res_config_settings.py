# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_rework_orders_action = fields.Selection([
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ], string='Rework Orders', default='automatic',
    config_parameter='mrp_extended.mrp_rework_orders_action')
    reworkcenter_id = fields.Many2one('mrp.workcenter',
        string="Default Rework Center",
        required=True, default=lambda self: self.env.ref('mrp_extended.rework_station', raise_if_not_found=False) or False,
        config_parameter='mrp_extended.default_reworkcenter_id')
