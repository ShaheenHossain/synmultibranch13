# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('workorder_id', False) and not self._context.get('is_finished_lot_id', False):
            workorder_id = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
            if not workorder_id.is_reworkorder and workorder_id.component_id and workorder_id.component_id.tracking != "none":
                unused_component_lots = workorder_id._get_unused_component_lots()
                if unused_component_lots:
                    args += [('id', 'in', unused_component_lots.ids)]
                else:
                    args += [('id', 'in', [])]
        if self._context.get('workorder_id', False) and self._context.get('is_finished_lot_id', False):
            workorder_id = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
            if not workorder_id.is_reworkorder:
                previously_finished_lots = workorder_id._get_previously_finished_lots()
                reworkorder_id = workorder_id.production_id.workorder_ids.filtered(lambda wo: wo.is_reworkorder)
                if reworkorder_id:
                    previously_finished_lots -= reworkorder_id._defaults_from_to_reworkorder_line().filtered(
                            lambda rewol: rewol.lot_id and rewol.rework_state == "pending"
                        ).mapped('lot_id')
                if previously_finished_lots:
                    args += [('id', 'in', previously_finished_lots.ids)]
                else:
                    args += [('id', 'in', [])]
            else:
                to_reworkorder_line_ids = workorder_id._defaults_from_to_reworkorder_line().filtered(
                        lambda rewol: rewol.lot_id and rewol.rework_state == "pending"
                    )
                if to_reworkorder_line_ids:
                    args = [('id', 'in', to_reworkorder_line_ids.mapped('lot_id').ids)]
                else:
                    args = [('id', 'in', [])]
        return super(StockProductionLot, self).name_search(name=name, args=args, operator=operator, limit=limit)
