# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields, api


class MrpPartialCloseConfirmation(models.TransientModel):
    _name = 'mrp_partial_close.confirmation'
    _description = "MRP Production Partial Close Confirmation"

    @api.model
    def default_get(self, fields):
        res = super(MrpPartialCloseConfirmation, self).default_get(fields)
        if self._context.get('active_id', False):
            mo = self.env['mrp.production'].browse(self._context['active_id'])
            if mo.exists():
                res.update({
                    'mo_id': mo.id,
                    'remain_qty': (mo.product_qty - mo.qty_produced),
                })
        return res

    mo_id = fields.Many2one('mrp.production', string="Manufacture Order")
    remain_qty = fields.Float(string="Remain Quantity", digits='Unit of Measure',
        required=True, readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Product Unit of Measure',
        related='mo_id.product_uom_id', readonly=True)
    reason = fields.Text(string="Reason", help="Reason for partial close manufacturing order.")

    def confirm_close(self):
        self.ensure_one()
        if not self.mo_id:
            return False
        return self.mo_id._mark_partial_done(self.reason)
