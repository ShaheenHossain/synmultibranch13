# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.model
    def name_search(self, name, args, operator='ilike', limit=100):
        if self._context.get('workorder_id', False) and not self._context.get('is_finished_lot_id', False):
            workorder_id = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
            if not workorder_id.is_reworkorder and workorder_id.component_id and workorder_id.component_id.tracking != "none":
                reserved_lots = workorder_id.move_line_ids.filtered(
                        lambda ml: ml.product_id.id == workorder_id.component_id.id
                    ).mapped('lot_id')
                lots_to_rework = workorder_id.to_reworkorder_line_ids.mapped('move_line_id').mapped('lot_id')
                reserved_lots = (reserved_lots - lots_to_rework)
                args += [('id', 'in', reserved_lots.ids)]
        if self._context.get('workorder_id', False) and self._context.get('is_finished_lot_id', False):
            workorder_id = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
            if not workorder_id.is_reworkorder:
                previous_wo = self.env['mrp.workorder'].search([
                    ('next_work_order_id', '=', self.id)
                ])
                if previous_wo:
                    finished_wo_line_in_previous_wo = workorder_id._defaults_from_finished_workorder_line(previous_wo.finished_workorder_line_ids)
                    if finished_wo_line_in_previous_wo:
                        args += [('id', 'in', finished_wo_line_in_previous_wo.mapped('lot_id').ids)]
                else:
                    args += [('id', 'in', [])]
            else:
                origin_wo = self.env['mrp.workorder'].search([
                    ('reworkorder_id', '=', workorder_id.id), ('production_id', '=', workorder_id.production_id.id)
                ])
                if origin_wo:
                    to_reworkorder_line_ids = workorder_id._defaults_from_to_reworkorder_line().filtered(lambda rewol: rewol.move_line_id and rewol.lot_id)
                    if to_reworkorder_line_ids:
                        args += [('id', 'in', to_reworkorder_line_ids.mapped('lot_id').ids)]
                else:
                    args += [('id', 'in', [])]
        return super(StockProductionLot, self).name_search(name, args=args, operator=operator, limit=limit)
