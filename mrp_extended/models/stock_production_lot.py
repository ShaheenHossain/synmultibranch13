# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


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
                previously_finished_lots = workorder_id._get_previously_finished_lots()
                if previously_finished_lots:
                    args += [('id', 'in', previously_finished_lots.ids)]
                else:
                    args += [('id', 'in', [])]
            else:
                to_reworkorder_line_ids = workorder_id._defaults_from_to_reworkorder_line().filtered(
                        lambda rewol: rewol.lot_id and rewol.rework_state == "pending"
                    )
                if to_reworkorder_line_ids:
                    if to_reworkorder_line_ids:
                        args += [('id', 'in', to_reworkorder_line_ids.mapped('lot_id').ids)]
                else:
                    args += [('id', 'in', [])]
        return super(StockProductionLot, self).name_search(name, args=args, operator=operator, limit=limit)
