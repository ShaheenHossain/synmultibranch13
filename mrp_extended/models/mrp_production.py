# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _create_reworkorder(self):
        default_reworkcenter_id = self.env["ir.config_parameter"].sudo().get_param("mrp_extended.default_reworkcenter_id")
        if not default_reworkcenter_id:
            raise UserError(_("Couldn\'t find default re-workcenter, Please configure re-workcenter first!"))

        # if configured in routing then no need to create reworkorder
        reworkorder = self.workorder_ids.filtered(lambda wo: wo.workcenter_id.id == int(default_reworkcenter_id))
        if reworkorder:
            return reworkorder

        # create reworkorder if not available
        reworkcenter_id = self.env['mrp.workcenter'].browse(int(default_reworkcenter_id))
        quantity = self.product_qty - sum(self.move_finished_ids.mapped('quantity_done'))
        quantity = quantity if (quantity > 0) else 0
        workorder = self.env['mrp.workorder'].create({
            'name': reworkcenter_id.name,
            'production_id': self.id,
            'workcenter_id': reworkcenter_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'operation_id': False,
            'state': 'pending',
            'is_reworkorder': True,
            'qty_producing': quantity,
            'consumption': self.bom_id.consumption,
        })
        return workorder

    def _generate_workorders(self, exploded_boms):
        workorders = super(MrpProduction, self)._generate_workorders(exploded_boms)
        default_reworkcenter_id = self.env["ir.config_parameter"].sudo().get_param("mrp_extended.default_reworkcenter_id")
        reworkorder = workorders.filtered(lambda wo: wo.workcenter_id.id == int(default_reworkcenter_id))
        reworkorder.write({'is_reworkorder': True})
        mrp_rework_orders_action = self.env["ir.config_parameter"].sudo().get_param("mrp_extended.mrp_rework_orders_action")
        if not reworkorder and mrp_rework_orders_action == "automatic":
            reworkorder = self._create_reworkorder()
        workorder_to_update = workorders.filtered(lambda wo: wo.next_work_order_id and wo.next_work_order_id.id == reworkorder.id)
        if workorder_to_update:
            workorder_to_update.write({'next_work_order_id': False})
        return workorders

