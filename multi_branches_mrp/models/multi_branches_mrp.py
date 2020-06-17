# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Returns domain of branch id by Company wise"""
        if self.company_id:
            self.branch_id = False
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            if len(branches) > 0:
                self.branch_id = branches[0]
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': [('id', 'in', [])]}}


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    branch_id = fields.Many2one('res.branch', string='Branch', related='bom_id.branch_id', readonly=False)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Returns domain of branch id by Company wise"""
        if self.company_id:
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            self.branch_id = False
            if len(branches) > 0:
                self.branch_id = branches[0]
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': [('id', 'in', [])]}}


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _get_default_picking_type(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        branch_id = self.env.user.branch_id.id
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', '=', company_id),
            ('warehouse_id.branch_id', '=', branch_id)
        ], limit=1).id

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id), ('branch_id', '=', branch_id)]",
        default=_get_default_picking_type, required=True, check_company=True)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Returns domain of branch id by Company wise"""
        if self.company_id:
            self.branch_id = False
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            if len(branches) > 0:
                self.branch_id = branches[0]
            if self.product_id:
                bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')
                if bom and bom.branch_id and (bom.branch_id.id in branches):
                    branches = bom.branch_id.ids
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': [('id', 'in', [])]}}

    @api.onchange('product_id', 'picking_type_id')
    def _onchange_product_id(self):
        """ Return domain of branch id by BOM wise"""
        if not self.bom_id and self.product_id:
            bom = self.env['mrp.bom']._bom_find(product=self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')
            if bom:
                self.branch_id = bom.branch_id.id
                return {'domain': {'branch_id': [('id', 'in', bom.branch_id.ids)]}}
        if self.bom_id and self.bom_id.type == 'normal':
            self.branch_id = self.bom_id.branch_id.id
            return {'domain': {'branch_id': [('id', 'in', self.bom_id.branch_id.ids)]}}

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        res = super(MrpProduction, self)._onchange_bom_id()
        if self.bom_id:
            self.branch_id = self.bom_id.branch_id.id
            self.picking_type_id = self.env['stock.picking.type'].search([
                                                ('code', '=', 'mrp_operation'),
                                                ('company_id', '=', self.company_id.id),
                                                ('branch_id', '=', self.branch_id.id)
                                            ], limit=1).id
            return {'domain': {'branch_id': [('id', 'in', self.bom_id.branch_id.ids)]}}
        return res

    def _get_move_raw_values(self, bom_line, line_data):
        data = super(MrpProduction, self)._get_move_raw_values(bom_line=bom_line, line_data=line_data)
        data.update({'branch_id': bom_line.branch_id.id})
        return data

    def _generate_workorders(self, exploded_boms):
        workorders = super(MrpProduction, self)._generate_workorders(exploded_boms=exploded_boms)
        for workorder in workorders:
            workorder.branch_id = workorder.production_id.branch_id.id
            for move_line in workorder.move_line_ids:
                move_line.branch_id = workorder.production_id.branch_id.id
        return workorders

    def _get_finished_move_value(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        values = super(MrpProduction, self)._get_finished_move_value(product_id=product_id, product_uom_qty=product_uom_qty, product_uom=product_uom, operation_id=operation_id, byproduct_id=byproduct_id)
        values.update({'branch_id': self.branch_id.id})
        return values

    @api.depends('move_finished_ids.move_line_ids')
    def _compute_lines(self):
        res = super(MrpProduction, self)._compute_lines()
        for production in self:
            for move_line in production.finished_move_line_ids:
                move_line.update({'branch_id': production.branch_id.id})
        return res


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id)
