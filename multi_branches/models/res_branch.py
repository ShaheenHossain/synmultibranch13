# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Branch(models.Model):
    _name = 'res.branch'
    _description = " Branch"

    def copy(self, default=None):
        raise UserError(_('Duplicating a branch is not allowed. Please create a new branch instead.'))

    @api.model
    def _get_euro(self):
        return self.env['res.currency.rate'].search([('rate', '=', 1)], limit=1).currency_id

    @api.model
    def _get_user_currency(self):
        currency_id = self.env.user.company_id.currency_id
        return currency_id or self._get_euro()

    def _get_branch_address_fields(self, partner):
        return {
            'street': partner.street,
            'street2': partner.street2,
            'city': partner.city,
            'zip': partner.zip,
            'state_id': partner.state_id,
            'country_id': partner.country_id,
        }

    # TODO @api.depends(): currently now way to formulate the dependency on the
    # partner's contact address
    def _compute_address(self):
        for branch in self.filtered(lambda branch: branch.partner_id):
            address_data = branch.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = branch.partner_id.browse(address_data['contact']).sudo()
                branch.update(branch._get_branch_address_fields(partner))

    def _inverse_street(self):
        for branch in self:
            branch.partner_id.street = branch.street

    def _inverse_street2(self):
        for branch in self:
            branch.partner_id.street2 = branch.street2

    def _inverse_zip(self):
        for branch in self:
            branch.partner_id.zip = branch.zip

    def _inverse_city(self):
        for branch in self:
            branch.partner_id.city = branch.city

    def _inverse_state(self):
        for branch in self:
            branch.partner_id.state_id = branch.state_id

    def _inverse_country(self):
        for branch in self:
            branch.partner_id.country_id = branch.country_id

    name = fields.Char(related='partner_id.name', string='Branch Name', required=True, store=True, readonly=False)
    logo = fields.Binary(related='partner_id.image_1920', string="Branch Logo", readonly=False)
    sequence = fields.Integer(help='Used to order Branches in the branch switcher')
    street = fields.Char(compute='_compute_address', inverse='_inverse_street', store=True)
    street2 = fields.Char(compute='_compute_address', inverse='_inverse_street2', store=True)
    zip = fields.Char(compute='_compute_address', inverse='_inverse_zip', store=True)
    city = fields.Char(compute='_compute_address', inverse='_inverse_city', store=True)
    state_id = fields.Many2one('res.country.state', compute='_compute_address', inverse='_inverse_state', string="Fed. State", store=True)
    email = fields.Char(related='partner_id.email', store=True, readonly=False)
    phone = fields.Char(related='partner_id.phone', store=True, readonly=False)
    website = fields.Char(related='partner_id.website', readonly=False)
    country_id = fields.Many2one('res.country', string="Country")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._get_user_currency())
    internal_transit_location_id = fields.Many2one(
        'stock.location', 'Internal Transit Location', on_delete="restrict",
        help="Technical field used for resupply routes between warehouses that belong to this branch")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The branch name must be unique !')
    ]

    @api.onchange('state_id')
    def _onchange_state(self):
        self.country_id = self.state_id.country_id

    def on_change_country(self, country_id):
        # This function is called from account/models/chart_template.py, hence decorated with `multi`.
        self.ensure_one()
        currency_id = self._get_user_currency()
        if country_id:
            currency_id = self.env['res.country'].browse(country_id).currency_id
        return {'value': {'currency_id': currency_id.id}}

    @api.onchange('country_id')
    def _onchange_country_id_wrapper(self):
        res = {'domain': {'state_id': []}}
        if self.country_id:
            res['domain']['state_id'] = [('country_id', '=', self.country_id.id)]
        values = self.on_change_country(self.country_id.id)['value']
        for fname, value in values.items():
            setattr(self, fname, value)
        return res

    def _create_transit_location(self):
        parent_location = self.env.ref('stock.stock_location_locations', raise_if_not_found=False)
        for company in self:
            location = self.env['stock.location'].create({
                'name': _('%s: Transit Location') % self.name,
                'usage': 'transit',
                'location_id': parent_location and parent_location.id or False,
                'company_id': self.company_id.id,
                'branch_id' : self.id,
            })
            company.write({'internal_transit_location_id': location.id})
            company.partner_id.with_context(force_branch=self.id).write({
                'property_stock_customer': location.id,
                'property_stock_supplier': location.id,
            })

    def inactive(self):
        warehouses = self.env['stock.warehouse'].search([('branch_id', '=', False)])
        locations = self.env['stock.location'].search([('branch_id', '=', False)])
        pickings = self.env['stock.picking.type'].search([])
        if warehouses:
            for warehouse in warehouses:
                warehouse.write({'active': False})
                for route_id in warehouse.route_ids:
                    route_id.write({'active': False})
        if locations:
            for location in locations:
                if location.company_id.id is not False:
                    location.write({'active': False})
        if pickings:
            for picking in pickings:
                if not picking.warehouse_id.branch_id.id:
                    picking.write({'active': False})

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals.get('partner_id'):
            self.clear_caches()
            return super(Branch, self).create(vals)
        partner = self.env['res.partner'].create({
            'name': vals['name'],
            'company_id': vals.get('company_id'),
            'image_1920': vals.get('logo'),
            'email': vals.get('email'),
            'phone': vals.get('phone'),
            'website': vals.get('website')
        })
        vals['partner_id'] = partner.id
        self.clear_caches()
        branch = super(Branch, self).create(vals)
        self.env.user.write({'branch_ids': [(4, branch.id)]})
        partner.write({'branch_id': branch.id})
        branch._create_transit_location()
        # multi-branch rules prevents creating warehouse and sub-locations
        self.env['stock.warehouse'].check_access_rights('create')
        self.env['stock.warehouse'].sudo().create({'partner_id': branch.partner_id.id, 'branch_id': branch.id, 'name': branch.name, 'code': branch.name[:5], 'company_id': branch.company_id.id})
        # self.inactive()
        return branch

    def write(self, values):
        self.clear_caches()
        return super(Branch, self).write(values)

    @api.model
    def name_search(self, name, args, operator='ilike', limit=100):
        if self._context.get('branch_id', False):
            branch_ids = self._context.get('branch_id', False)
            for branch in branch_ids:
                for ids in branch[2:]:
                    if len(ids) > 0:
                        args.append(('id', 'in', ids))
                    else:
                        args.append(('id', 'in', []))
        if self._context.get('company_id', False):
            branches = self.env.user.branch_ids.filtered(lambda m: m.company_id.id == self._context.get('company_id')).ids
            if branches:
                args.append(('id', 'in', branches))
        return super(Branch, self).name_search(name, args=args, operator=operator, limit=limit)
