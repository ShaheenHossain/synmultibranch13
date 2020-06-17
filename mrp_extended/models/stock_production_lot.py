# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.osv import expression
from odoo import api, fields, models, _


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    def _compute_finished_product(self):
        for rec in self:
            rec.qty_finished_product = len(rec._get_finished_lot_ids().ids)

    qty_finished_product = fields.Integer('Finished Product Quantity', compute='_compute_finished_product')

    def _get_finished_lot_ids(self):
        self.ensure_one()
        StockProductionLot = self.env['stock.production.lot']
        MoveLine = self.env['stock.move.line']
        StockProductionLot |= MoveLine.search([
                                ('product_id', '=', self.product_id.id),
                                ('lot_id', '=', self.id),
                                ('state', '=', 'done')
                            ]).mapped('lot_produced_ids')
        return StockProductionLot

    def action_open_finished_product(self):
        self.ensure_one()
        action = {
            'name': _('Finished Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.production.lot',
            'target': 'current',
        }
        finished_product_lot_ids = self._get_finished_lot_ids()
        if len(finished_product_lot_ids) == 1:
            action['res_id'] = finished_product_lot_ids[0].id
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', finished_product_lot_ids.ids)]
        return action

    def _get_mrp_workorder_search_domain(self):
        domain = list()
        if self._context.get('workorder_id', False) and not self._context.get('is_finished_lot_id', False):
            workorder_id = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
            if not workorder_id.is_reworkorder and workorder_id.component_id and workorder_id.component_id.tracking != "none":
                unused_component_lots = workorder_id._get_unused_component_lots()
                if unused_component_lots:
                    domain += [('id', 'in', unused_component_lots.ids)]
                else:
                    domain += [('id', 'in', [])]
        if self._context.get('workorder_id', False) and self._context.get('is_finished_lot_id', False):
            workorder_id = self.env['mrp.workorder'].browse(self._context.get('workorder_id'))
            if not workorder_id.is_reworkorder:
                # Prvious workorder lots
                previously_finished_lots = workorder_id._get_previously_finished_lots()
                # Current workorder lots
                previously_finished_lots -= workorder_id.finished_workorder_line_ids.mapped('lot_id')
                # Re-workorder lots
                reworkorder_id = workorder_id.production_id.workorder_ids.filtered(lambda wo: wo.is_reworkorder)
                if reworkorder_id:
                    previously_finished_lots -= reworkorder_id._defaults_from_to_reworkorder_line().filtered(
                            lambda rewol: rewol.lot_id and rewol.rework_state == "pending"
                        ).mapped('lot_id')
                if previously_finished_lots:
                    domain += [('id', 'in', previously_finished_lots.ids)]
                else:
                    domain += [('id', 'in', [])]
            else:
                to_reworkorder_line_ids = workorder_id._defaults_from_to_reworkorder_line().filtered(
                        lambda rewol: rewol.lot_id and rewol.rework_state == "pending"
                    )
                if to_reworkorder_line_ids:
                    domain = [('id', 'in', to_reworkorder_line_ids.mapped('lot_id').ids)]
                else:
                    domain = [('id', 'in', [])]
        return domain

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        ''' @Override: to restrict lots which are not in MRP production or in MRP reworkorder '''
        domain = domain or []
        if self._context.get('workorder_id', False) or self._context.get('is_finished_lot_id', False):
            user_domain = self._get_mrp_workorder_search_domain()
            domain = expression.AND([domain, user_domain])
        return super(StockProductionLot, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ''' @Override: to restrict lots which are not in MRP production or in MRP reworkorder '''
        if self._context.get('workorder_id', False) or self._context.get('is_finished_lot_id', False):
            args = self._get_mrp_workorder_search_domain()
        return super(StockProductionLot, self).name_search(name=name, args=args, operator=operator, limit=limit)
