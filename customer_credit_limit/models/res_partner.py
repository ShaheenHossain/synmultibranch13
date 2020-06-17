# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_limit = fields.Float("Credit Limit", help="Credit Limit to manage customer outstanding debts.")
    name_on_board = fields.Char("Name On Board", help="Name on board for customer.")
    is_distributor = fields.Boolean("Destributor")
    cr_no = fields.Char("CR", help="CR Number")
    cr_issue_date = fields.Date("Issue Date", help="CR Issue Date")
    cr_expiry_date = fields.Date("Expiry Date", help="CR Expiry Date")
    license_no = fields.Char("License", help="License Number")
    license_issue_date = fields.Date("Issue Date", help="License Issue Date")
    license_expiry_date = fields.Date("Expiry Date", help="License Expiry Date")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = []
        if name and name.strip != '' and operator in ('ilike', 'like', '=', '=like', '=ilike'):
            domain = expression.AND([
                args or [],
                ['|', ('name', operator, name), ('name_on_board', operator, name)]
            ])
            order_ids = self._search(domain, limit=limit, access_rights_uid=name_get_uid)
            return models.lazy_name_get(self.browse(order_ids).with_user(name_get_uid))
        return super(ResPartner, self)._name_search(name, args=args, operator=operator, limit=limit,
                                                        name_get_uid=name_get_uid)
