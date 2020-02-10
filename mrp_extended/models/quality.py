# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class QualityPoint(models.Model):
    _inherit = "quality.point"

    rework_process = fields.Selection([
            ('auto', "Automatic"),
            ('manual', "Manual"),
        ], default='auto', string="Rework Process")
