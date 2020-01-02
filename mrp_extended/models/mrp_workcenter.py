# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    team_id = fields.Many2one("mrp.team", string="MRP Team",
        help="Team related to workcenter.")
