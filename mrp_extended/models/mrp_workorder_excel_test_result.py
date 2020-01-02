# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, fields


class MrpWorkorderExcelTestResult(models.Model):
    _name = "mrp.workorder.excel_test_result"
    _description = "MRP Workorder Excel Test Result"

    sta = fields.Selection([
        ("pass", "Pass"),
        ("fail", "Fail")], string="STA", help="STA Test Result")
    crp = fields.Selection([
        ("pass", "Pass"),
        ("fail", "Fail")], string="CRP", help="CRP Test Result")
    votage_test = fields.Selection([
        ("pass", "Pass"),
        ("fail", "Fail")], string="Votage Test", help="Votage Test Result")
    result = fields.Selection([
        ("pass", "Pass"),
        ("fail", "Fail")], string="Result", help="Test Result")
    component_lot_ref = fields.Char(string='Asset No.')
    finish_lot_ref = fields.Char(string='Product No.')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', 'Workorder', ondelete='cascade')

