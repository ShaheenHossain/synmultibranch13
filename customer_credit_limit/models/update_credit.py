# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta


class UpdateCredit(models.Model):
    _name = "update.credit"
    _description = "Update Credit"
    _order = "id desc"

    name = fields.Char("Name", help="Record Name")
    date_time = fields.Datetime("Date", help="Date - Time when update credit limit was processed.")
    user_id = fields.Many2one("res.users", string="Responsible",
                              help="Responsible User for update credit limit process.")
    update_credit_line_ids = fields.One2many("update.credit.line", "update_credit_id", string="Update Credit Lines",
                                             required=True, help="Update Credit Lines")
    quarter = fields.Selection([('1', '1'),
                                ('2', '2'),
                                ('3', '3'),
                                ('4', '4'),
                                ('custom', 'Custom')], string="Quarter", default="custom", required=True,)
    state = fields.Selection([("draft", "Draft"),
                              ("waiting_approval", "Waiting Approval"),
                              ("done", "Done"),
                              ("cancel", "Cancel")], string="State", default="draft")

    @api.model
    def default_get(self, fields):
        res = super(UpdateCredit, self).default_get(fields)
        res.update({
            'name': _('New'),
            'date_time': datetime.now(),
            'user_id': self.env.user.id,
        })
        return res

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('update.credit.sequence') or _('New')
        vals.update({'name': name})
        return super(UpdateCredit, self).create(vals)

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise Warning(_("You can delete only draft records."))
        return super(UpdateCredit, self).unlink()

    def action_confirm(self):
        return self.write({"state": "waiting_approval"})

    def action_done(self):
        for record in self:
            for line in record.update_credit_line_ids:
                line.partner_id.write({"credit_limit": line.new_credit})
        self.write({"state": "done"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def get_calculated_credit(self, partner, calculate_days):
        collection_period = partner.property_payment_term_id and max(partner.property_payment_term_id.line_ids.mapped("days")) or 0.0
        today = datetime.now().date()
        past_day = datetime.now().date() - relativedelta(days=calculate_days)
        if collection_period > 0.0:
            invoices = self.env["account.move"].search(
                [('invoice_date', '>=', past_day), ('invoice_date', '<=', today), ('partner_id', '=', partner.id)])
            total_amount_invoiced = sum(invoices.mapped("amount_total"))
            total_amount_residual = sum(invoices.mapped("amount_residual"))
            collection_amount = total_amount_invoiced - total_amount_residual
            new_credit_limit = (collection_amount / collection_period)*120
            return round(new_credit_limit, 2)

        return partner.credit_limit

    def create_update_credit_limit_record_cron(self):
        partners = self.env["res.partner"].search([('credit_limit', '>', 0.0)]).mapped("commercial_partner_id")
        line_data = []
        current_month = datetime.now().month
        current_date = datetime.now().month
        calculate_days = 0
        quarter = 'custom'
        if current_month >= 1 and current_month <= 3:
            calculate_days = 365
            if current_date == 1 and current_month == 1:
                quarter = '1'
        elif current_month >= 4 and current_month <= 6:
            calculate_days = 90
            if current_date == 1 and current_month == 4:
                quarter = '2'
        elif current_month >= 7 and current_month <= 9:
            calculate_days = 180
            if current_date == 1 and current_month == 7:
                quarter = '3'
        elif current_month >= 10 and current_month <= 12:
            calculate_days = 270
            if current_date == 1 and current_month == 10:
                quarter = '4'

        for partner in partners:
            calculated_credit = self.get_calculated_credit(partner, calculate_days)
            line_data.append((0, 0, {"partner_id": partner.id,
                                     "old_credit": partner.credit_limit,
                                     "calculated_credit": calculated_credit,
                                     "new_credit": calculated_credit,
                                     }))
        vals = {
            "name": datetime.now(),
            "date_time": datetime.now(),
            "user_id": self.env.user.id,
            "state": "draft",
            "quarter": quarter,
            "update_credit_line_ids": line_data
        }
        return self.env["update.credit"].create(vals)


class UpdateCreditLine(models.Model):
    _name = "update.credit.line"
    _description = "Update Credit Line"
    _order = "id"

    update_credit_id = fields.Many2one("update.credit", string="Update Credit", copy=False, ondelete="cascade",
                                       help="Related Update Credit")
    partner_id = fields.Many2one("res.partner", string="Customer", required=True, copy=False, help="Related Partner.")
    old_credit = fields.Float("Old Credit", copy=False)
    calculated_credit = fields.Float("Calculated Credit", copy=False)
    new_credit = fields.Float("New Credit", copy=False)

    @api.onchange("partner_id")
    def onchange_partner_id(self):
        current_month = datetime.now().month
        calculate_days = 0
        if current_month >= 1 and current_month <= 3:
            calculate_days = 365
        elif current_month >= 4 and current_month <= 6:
            calculate_days = 90
        elif current_month >= 7 and current_month <= 9:
            calculate_days = 180
        elif current_month >= 10 and current_month <= 12:
            calculate_days = 270
        calculated_credit = self.update_credit_id.get_calculated_credit(self.partner_id, calculate_days)
        self.calculated_credit = calculated_credit or 0.0
        self.old_credit = self.partner_id.credit_limit or 0.0
