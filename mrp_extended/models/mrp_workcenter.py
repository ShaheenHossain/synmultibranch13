# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    use_create_lot_from_comp_lot = fields.Boolean(default=False,
        string="Create Finish SN From Component SN",
        help="Enables create/assign finish SN from component SN,\
        basically used in first sequential workorder.")
    team_id = fields.Many2one("mrp.team", string="MRP Team",
        help="Team related to workcenter.")
