# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    def _default_branch_id(self):
        branch_id = self.env.user.branch_id.id
        if self._context.get('branch_id'):
            branch_id = self._context.get('branch_id')
        return branch_id

    branch_id = fields.Many2one("res.branch", string='Branch', default=_default_branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id and not self._context.get('branch_id'):
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            if len(branches) > 0:
                self.branch_id = branches[0]
            else:
                self.branch_id = False
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': []}}

    def action_invoice_register_payment(self):
        return self.env['account.payment']\
            .with_context(active_ids=self.ids, active_model='account.move', active_id=self.id, branch_id=self.branch_id.id)\
            .action_register_payment()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # OVERRIDE
        if not default_values_list:
            default_values_list = [{} for move in self]
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'branch_id': move.branch_id.id,
            })
        return super(AccountInvoice, self)._reverse_moves(default_values_list=default_values_list, cancel=cancel)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    branch_id = fields.Many2one("res.branch", string='Branch', related='move_id.branch_id', store=True)


class AccountPayments(models.Model):
    _inherit = 'account.payment'

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayments, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            rec['branch_id'] = invoice.get('branch_id') and invoice.get('branch_id')[0]
        return rec

    branch_id = fields.Many2one("res.branch", string='Branch', default=lambda self: self.env.user.branch_id)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id and not self._context.get('branch_id'):
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self.company_id.id).ids
            if len(branches) > 0:
                self.branch_id = branches[0]
            else:
                self.branch_id = False
            return {'domain': {'branch_id': [('id', 'in', branches)]}}
        else:
            return {'domain': {'branch_id': []}}

    def _prepare_payment_moves(self):
        all_move_vals = super(AccountPayments, self)._prepare_payment_moves()
        for move in all_move_vals:
            move.update({'branch_id': self.branch_id.id})
            for line in move.get('line_ids'):
                line[2].update({'branch_id': self.branch_id.id})
        return all_move_vals
