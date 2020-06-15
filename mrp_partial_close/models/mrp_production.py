# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.tools import float_compare
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.depends('product_qty', 'qty_produced', 'state')
    def _check_partial_done(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for production in self:
            if production.state == "done" and float_compare(
                        production.product_qty,
                        production.qty_produced,
                        precision_digits=precision
                    ) != 0:
                production.is_partial_done = True

    qty_produced = fields.Float(digits='Product Unit of Measure')
    product_uom_id2 = fields.Many2one('uom.uom', related='product_uom_id', string='Unit of Measure', readonly=True)
    is_partial_done = fields.Boolean(string="Partial Done", compute='_check_partial_done', store=True,
        help="Technical field to track is MO partial done or not.")
    partial_close_reason = fields.Text(string="Partial Close Reason")

    def _mark_partial_done(self, reason=""):
        # unlink lots if work order line rework_state in 'to_unbuild'
        reworkorder_id = self.workorder_ids.filtered(lambda wo: wo.is_reworkorder)
        if reworkorder_id:
            reworkorder_lines = reworkorder_id._defaults_from_to_reworkorder_line()
            if reworkorder_id.state not in ('pending', 'done', 'cancel') and\
                reworkorder_lines and ('to_unbuild' in reworkorder_lines.mapped('rework_state')):
                StockQuant = self.env['stock.quant']
                lots_to_delete = self.env['stock.production.lot']
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                created_lots = reworkorder_lines.filtered(lambda re: re.rework_state == 'to_unbuild').mapped('lot_id')
                for lot in created_lots:
                    # Ensure that created lot has not quant available
                    if float_compare(StockQuant._get_available_quantity(
                        reworkorder_id.product_id,
                        reworkorder_id.production_id.location_dest_id,
                        lot_id=lot,
                        strict=True
                    ), 0, precision_digits=precision) <= 0:
                        lots_to_delete |= lot

                lots_to_delete.unlink()

        # post inventory and mark as done
        self.button_mark_done()

        # adjust rework order start/end dates if not started
        reworkorder_id = self.workorder_ids.filtered(lambda wo: wo.is_reworkorder)
        if reworkorder_id:
            reworkorder_id._adjust_reworkorder_dates()

        # finish all workorder
        for wo in self.workorder_ids:
            wo.button_finish()

        if reason:
            self.write({'partial_close_reason': reason})
        return True

    def button_mark_partial_done(self):
        self.ensure_one()

        # check for rework order
        reworkorder_id = self.workorder_ids.filtered(lambda wo: wo.is_reworkorder)
        if reworkorder_id:
            reworkorder_lines = reworkorder_id._defaults_from_to_reworkorder_line()
            if reworkorder_id.state not in ('pending', 'done', 'cancel') and\
                reworkorder_lines and ('pending' in reworkorder_lines.mapped('rework_state')):
                error_msg = _("%s is currently in progress for rework of following:\n") % (reworkorder_id.display_name)
                for rewol in reworkorder_lines:
                    error_msg += "{} ({} - {} {})\n".format(
                            self.product_id.display_name,
                            rewol.lot_id.name,
                            rewol.qty_to_consume,
                            rewol.product_uom_id.name
                        )
                raise UserError(error_msg)

        context = dict(self.env.context or {})
        context.update(active_id=self.id)

        return {
            'name': _('Confirm Partial Close'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'res_model': 'mrp_partial_close.confirmation',
            'target': 'new',
            'context': context,
        }
