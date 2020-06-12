# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            self.branch_id = False
            if len(branches) > 0:
                self.branch_id = branches[0]
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': []}}

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            warehouse = self.env['stock.warehouse'].search([('branch_id', '=', self.branch_id.id)])
            self.warehouse_id = False
            if self.branch_id and warehouse:
                self.warehouse_id = warehouse[0].id
            return {'domain': {'warehouse_id': [('id', 'in', warehouse.ids)]}}
        else:
            return {'domain': {'warehouse_id': []}}

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({'branch_id': self.branch_id.id})
        return invoice_vals
