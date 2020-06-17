# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, models, fields


class MrpWorkorderUnbuildConfirmation(models.TransientModel):
    _name = "mrp.workorder.unbuild.confirmation"
    _description = "Mrp Workorder Unbuild Confirmation"

    @api.model
    def default_get(self, fields):
        res = super(MrpWorkorderUnbuildConfirmation, self).default_get(fields)
        if self._context.get('active_id', False) and self._context.get('active_model') == 'mrp.workorder':
            wo_id = self.env['mrp.workorder'].browse(self._context['active_id'])
            res.update({
                'workorder_id': wo_id.id,
                'product_name': wo_id.product_id.display_name,
                'finished_lot_name': wo_id.finished_lot_id and wo_id.finished_lot_id.name or "",
            })
        return res

    workorder_id = fields.Many2one('mrp.workorder', string="Workorder", readonly=True)
    product_name = fields.Char(string="finish Product", readonly=True)
    finished_lot_name = fields.Char(string="Product Lot", readonly=True)

    def action_confirm(self):
        self.ensure_one()
        return self.workorder_id.do_unbuild()
