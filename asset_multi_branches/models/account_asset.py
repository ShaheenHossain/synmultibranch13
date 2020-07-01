# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)
