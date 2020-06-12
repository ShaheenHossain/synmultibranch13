# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def default_get(self, fields):
        res = super(StockMove, self).default_get(fields)
        if res.get('raw_material_production_id'):
            production_id = self.env['mrp.production'].browse(res['raw_material_production_id'])
            res.update({'branch_id': production_id.branch_id.id})
        return res

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Returns domain of branch id by Company wise"""
        if self.company_id:
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': [('id', 'in', [])]}}


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Returns domain of branch id by Company wise"""
        if self.company_id:
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': [('id', 'in', [])]}}


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Returns domain of branch id by Company wise"""
        if self.company_id:
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': [('id', 'in', [])]}}
