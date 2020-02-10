# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields


class MrpTeam(models.Model):
    _name = "mrp.team"
    _description = "MRP Team"
    _order = "id desc"

    name = fields.Char(string="Name", help="MRP Team.")
    active = fields.Boolean(string='Active', default=True)
    user_ids = fields.Many2many("res.users", string="Users",
        help="Related Users.")
