# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo.tools import float_compare, float_round
from odoo.osv import expression
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    @api.depends(
        'current_quality_check_id',
        'to_reworkorder_line_ids',
        'to_reworkorder_line_ids.move_line_id',
        'to_reworkorder_line_ids.rework_state',
        'lot_id',
        'finished_lot_id'
    )
    def _check_has_rework(self):
        for wo in self:
            reworkorder_lines = wo.production_id.workorder_ids.filtered(
                    lambda workorder: not workorder.is_reworkorder
                ).mapped('to_reworkorder_line_ids')
            if wo.lot_id and wo.lot_id.id in reworkorder_lines.filtered(
                    lambda rewol: rewol.rework_state != "done"
                ).mapped('move_line_id').mapped('lot_id').ids:
                wo.has_rework = True
            elif reworkorder_lines.filtered(lambda rewol: wo.finished_lot_id and\
                wo.finished_lot_id.id == rewol.lot_id.id and rewol.rework_state != "done"):
                wo.has_rework = True
            else:
                wo.has_rework = False

    @api.depends('finished_lot_id')
    def _get_previously_finished_steps(self):
        for wokorder in self:
            if wokorder.finished_lot_id:
                prev_wos = wokorder.production_id.workorder_ids.filtered(lambda wo: wo.id < wokorder._origin.id)
                # get previously done quality check
                prev_finished_check_ids = prev_wos.check_ids.filtered(
                        lambda check: check.finished_lot_id and check.finished_lot_id.id == wokorder.finished_lot_id.id
                    )
                # get currently done quality check
                current_check_ids = wokorder.check_ids._origin.filtered(lambda check: check.finished_lot_id and check.finished_lot_id.id == wokorder.finished_lot_id.id)
                wokorder.previously_finished_check_ids = [(6, 0, (prev_finished_check_ids + current_check_ids).ids)]
            else:
                wokorder.previously_finished_check_ids = []

    @api.depends('to_reworkorder_line_ids', 'to_reworkorder_line_ids.rework_state', 'finished_reworkorder_line_ids')
    def _get_qty_rework(self):
        for wo in self:
            if not wo.is_reworkorder:
                wo.qty_rework = 0.0
            reworkorder_id = (wo.production_id.workorder_ids - wo).filtered(
                    lambda wokorder: wokorder.is_reworkorder
                )
            if reworkorder_id:
                reworkorder_lines = reworkorder_id._defaults_from_to_reworkorder_line()
                reworkorder_id.qty_rework = sum(reworkorder_lines.mapped('qty_done'))

    qty_rework = fields.Float('Rework Quantity', compute='_get_qty_rework', readonly=True, store=True)
    is_reworkorder = fields.Boolean("Is Rework Order",
        help="Check if workorder is rework order or not.")
    reworkorder_id = fields.Many2one("mrp.workorder", "Rework Station Workorder",
        help="Workorder in rework station to check rework process is done.")
    to_reworkorder_line_ids = fields.One2many('mrp.workorder.line',
        'orig_rewo_id', string='To Rework')
    finished_reworkorder_line_ids = fields.One2many('mrp.workorder.line',
        'finished_reworkorder_id', string='finished Re-Workorder Lines')
    previously_finished_check_ids = fields.Many2many('quality.check',
        compute='_get_previously_finished_steps', string='Previously Processed Steps')
    created_finished_lot_ids = fields.Many2many('stock.production.lot',
        string='Created Finish Product Lots/SN',
        help="Technical field to store created lots use to delete in case of MO will cancel.")
    has_rework = fields.Boolean(compute='_check_has_rework', store=True,
        help="Technical field to track SN has rework or not.")
    excel_test_result_ids = fields.One2many('mrp.workorder.excel_test_result',
        'workorder_id', string='Test Results', readonly=True)
    last_test_import_date = fields.Datetime("Last Test Import Date", readonly=True)
    last_test_import_user = fields.Many2one("res.users", "Last Test Import User", readonly=True)
    orig_move_line_id = fields.Many2one('stock.move.line', string="Move Line",
        help="Technical field to track related move of rework order line.")

    @api.depends('production_id.workorder_ids')
    def _compute_is_last_unfinished_wo(self):
        for wo in self:
            if not wo.is_reworkorder:
                other_wos = wo.production_id.workorder_ids.filtered(lambda wokorder: not wokorder.is_reworkorder) - wo
                other_states = other_wos.mapped(lambda w: w.state == 'done')
                wo.is_last_unfinished_wo = all(other_states)
            else:
                wo.is_last_unfinished_wo = False

    @api.depends('qty_production', 'qty_produced')
    def _compute_qty_remaining(self):
        for wo in self.filtered(lambda workorder: not workorder.is_reworkorder):
            wo.qty_remaining = float_round(wo.qty_production - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding)
        for rewo in self.filtered(lambda reworkorder: reworkorder.is_reworkorder):
            rewo.qty_remaining = float_round(rewo.qty_rework or 1, precision_rounding=rewo.production_id.product_uom_id.rounding)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        context = self._context or {}
        if context.get('reworkorder_id', False):
            for index in range(len(args)):
                if args[index][0] == "next_work_order_id" and isinstance(args[index][2], int) and args[index][2] == context['reworkorder_id']:
                    args[index] = ("reworkorder_id", args[index][1], args[index][2])
        return super(MrpWorkorder, self)._search(args=args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        ''' @Override: to limit the workorders for MRP users '''
        domain = domain or []
        if self.env.user.has_group('mrp.group_mrp_user') and not self.env.user.has_group('mrp.group_mrp_manager'):
            user_domain = ['|', ['workcenter_id.team_id', '=', False], ['workcenter_id.team_id.user_ids', 'child_of', [self.env.user.id]]]
            domain = expression.AND([domain, user_domain])
        return super(MrpWorkorder, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def _get_previously_finished_lots(self):
        self.ensure_one()
        Lots = self.env['stock.production.lot']
        if self.product_tracking != 'none':
            previous_wo = self.env['mrp.workorder'].search([
                ('next_work_order_id', '=', self.id)
            ])
            if previous_wo:
                Lots |= previous_wo.finished_workorder_line_ids.mapped('lot_id')
        return Lots

    def _get_unused_component_lots(self):
        self.ensure_one()
        Lots = self.env['stock.production.lot']
        reserved_lots = self.move_line_ids.filtered(
                lambda ml: ml.product_id.id == self.component_id.id
            ).mapped('lot_id')

        finished_lots = self.move_line_ids.filtered(
                lambda ml: float_compare(ml.qty_done, ml.product_uom_qty, precision_rounding=ml.product_uom_id.rounding) == 0
            ).mapped('lot_id')

        # get rework lines
        reworkorder_lines = self.production_id.workorder_ids.filtered(
                lambda workorder: not workorder.is_reworkorder
            ).mapped('to_reworkorder_line_ids')

        to_rework_lots = reworkorder_lines.filtered(
                lambda rewol: rewol.rework_state != "done"
            ).mapped('move_line_id').mapped('lot_id')
        # ignore finished and rework lots
        Lots |= ((reserved_lots - finished_lots) - to_rework_lots)
        return Lots

    def _defaults_from_to_reworkorder_line(self):
        self.ensure_one()
        to_reworkorder_line_ids = self.env['mrp.workorder.line']
        origin_wo_ids = self.env[self._name].search([
                ('reworkorder_id', '=', self.id)
            ])
        for wo in origin_wo_ids:
            to_reworkorder_line_ids |= wo.to_reworkorder_line_ids
        return to_reworkorder_line_ids

    def _defaults_from_finished_workorder_line(self, reference_lot_lines):
        if self.is_reworkorder:
            reference_lot_lines = reference_lot_lines.filtered(lambda rll: not rll.finished_workorder_id)
            for rework_line in self._defaults_from_to_reworkorder_line().filtered(lambda rewol: rewol.move_line_id):
                reference_lot_lines |= rework_line
        for r_line in reference_lot_lines:
            # see which lot we could suggest and its related qty_producing
            if not r_line.lot_id:
                continue
            candidates = self.finished_workorder_line_ids.filtered(lambda line: line.lot_id == r_line.lot_id)
            rounding = self.product_uom_id.rounding
            if not candidates:
                self.write({
                    'finished_lot_id': False,
                    'qty_producing': r_line.qty_done,
                    'orig_move_line_id': r_line.move_line_id.id,
                })
                return True
            elif float_compare(candidates.qty_done, r_line.qty_done, precision_rounding=rounding) < 0:
                self.write({
                    'finished_lot_id': False,
                    'qty_producing': r_line.qty_done - candidates.qty_done,
                    'orig_move_line_id': r_line.move_line_id.id,
                })
                return True
            elif self.is_reworkorder:
                self.write({
                    'finished_lot_id': r_line.lot_id.id,
                    'qty_producing': r_line.qty_done,
                    'orig_move_line_id': r_line.move_line_id.id,
                })
                return True
        return False

    # def _apply_update_workorder_lines(self):
    #     previous_wo = self.env[self._name].search([
    #                 ('next_work_order_id', '=', self.id)
    #             ])
    #     if previous_wo and previous_wo.reworkorder_id:
    #         return super(MrpWorkorder, previous_wo.reworkorder_id)._apply_update_workorder_lines()
    #     return super(MrpWorkorder, self)._apply_update_workorder_lines()

    @api.model
    def _generate_lines_values(self, move, qty_to_consume):
        """ Create workorder line. First generate line based on the reservation,
        in order to prefill reserved quantity, lot and serial number.
        If the quantity to consume is greater than the reservation quantity then
        create line with the correct quantity to consume but without lot or
        serial number.
        """
        lines = []
        is_tracked = move.product_id.tracking != 'none'
        if move in self.move_raw_ids._origin:
            # Get the inverse_name (many2one on line) of raw_workorder_line_ids
            initial_line_values = {self.raw_workorder_line_ids._get_raw_workorder_inverse_name(): self.id}
        else:
            # Get the inverse_name (many2one on line) of finished_workorder_line_ids
            initial_line_values = {self.finished_workorder_line_ids._get_finished_workoder_inverse_name(): self.id}

        # # finished and not in reworkorder
        # move_line_ids = move.move_line_ids.filtered(lambda ml: ml.lot_id and ml.lot_id.id not in self.to_reworkorder_line_ids.mapped('move_line_id').mapped('lot_id').ids)
        # if not move_line_ids and self.to_reworkorder_line_ids:
        #     move_line_ids = self.to_reworkorder_line_ids.mapped('move_line_id')

        move_line_ids = ((move.move_line_ids - move.move_line_ids.filtered(
                    lambda ml: ml.lot_produced_ids or float_compare(ml.product_uom_qty, ml.qty_done, precision_rounding=move.product_uom.rounding) <= 0
                )) - self.to_reworkorder_line_ids.mapped('move_line_id'))
        if not move_line_ids:
            move_line_ids = self.to_reworkorder_line_ids.mapped('move_line_id')
        for move_line in move_line_ids:
            line = dict(initial_line_values)
            if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) <= 0:
                break
            # move line already 'used' in workorder (from its lot for instance)
            if move_line.lot_produced_ids or float_compare(move_line.product_uom_qty, move_line.qty_done, precision_rounding=move.product_uom.rounding) <= 0:
                continue
            # search wo line on which the lot is not fully consumed or other reserved lot
            linked_wo_line = self._workorder_line_ids().filtered(
                lambda line: line.move_id == move and
                line.lot_id == move_line.lot_id
            )
            if linked_wo_line:
                if float_compare(sum(linked_wo_line.mapped('qty_to_consume')), move_line.product_uom_qty - move_line.qty_done, precision_rounding=move.product_uom.rounding) < 0:
                    to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty - move_line.qty_done - sum(linked_wo_line.mapped('qty_to_consume')))
                else:
                    continue
            else:
                to_consume_in_line = min(qty_to_consume, move_line.product_uom_qty - move_line.qty_done)
            line.update({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': is_tracked and move.product_id.uom_id.id or move.product_uom.id,
                'qty_to_consume': to_consume_in_line,
                'qty_reserved': to_consume_in_line,
                'lot_id': move_line.lot_id.id,
                'move_line_id': move_line.id,
                'qty_done': to_consume_in_line,
            })
            lines.append(line)
            qty_to_consume -= to_consume_in_line
        # The move has not reserved the whole quantity so we create new wo lines
        if float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
            line = dict(initial_line_values)
            if move.product_id.tracking == 'serial':
                while float_compare(qty_to_consume, 0.0, precision_rounding=move.product_uom.rounding) > 0:
                    line.update({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_id.uom_id.id,
                        'qty_to_consume': 1,
                        'qty_done': 1,
                    })
                    lines.append(line)
                    qty_to_consume -= 1
            else:
                line.update({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'qty_to_consume': qty_to_consume,
                    'qty_done': qty_to_consume,
                })
                lines.append(line)
        steps = self._get_quality_points(lines)
        for line in lines:
            if line['product_id'] in steps.mapped('component_id.id') or move.has_tracking != 'none':
                line['qty_done'] = 0
        return lines

    def do_rework(self, auto=False):
        self.ensure_one()
        check_id = self.current_quality_check_id
        if self.component_tracking == "serial" and not self.lot_id:
            raise UserError(_("Please enter a serial number for component!."))
        if not check_id and self.product_tracking == "serial" and not self.finished_lot_id:
            raise UserError(_("Please enter a serial number for product!."))

        # Create or Update Rework Order
        mrp_rework_orders_action = self.env["ir.config_parameter"].sudo().get_param("mrp_extended.mrp_rework_orders_action")
        default_reworkcenter_id = self.env["ir.config_parameter"].sudo().get_param("mrp_extended.default_reworkcenter_id")
        self.reworkorder_id = self.production_id.workorder_ids.filtered(
                lambda wo: wo.workcenter_id.id == int(default_reworkcenter_id) and wo.state not in ('cancel', 'done') and wo.is_reworkorder
            )
        if mrp_rework_orders_action == "manual" and not self.reworkorder_id:
            self.reworkorder_id = self.production_id._create_reworkorder()

        self.reworkorder_id.with_context(force_date=True).write({
            'date_planned_start': self.date_planned_start,
            'date_planned_finished': self.date_planned_finished,
            'state': 'ready',
        })

        # Link related move line to the work order line
        move_line_id = False
        if self.lot_id:
            move_finished_ids = self.move_finished_ids.filtered(lambda move: move.product_id != self.product_id and move.state not in ('done', 'cancel'))
            move_raw_ids = self.move_raw_ids.filtered(lambda move: move.state not in ('done', 'cancel'))
            for move in move_raw_ids | move_finished_ids:
                move_line_ids = ((move.move_line_ids - move.move_line_ids.filtered(
                            lambda ml: ml.lot_produced_ids or float_compare(ml.product_uom_qty, ml.qty_done, precision_rounding=move.product_uom.rounding) <= 0
                        )) - self.to_reworkorder_line_ids.mapped('move_line_id'))
                move_line_id = move_line_ids.filtered(lambda ml: ml.lot_id and ml.lot_id.id == self.lot_id.id)
                if move_line_id:
                    break

        # Ensure that product or component has tracking is not none
        if self.component_tracking == "serial" and self.product_tracking == "serial":
            self._assign_component_lot_to_finish_lot()
            self.raw_workorder_line_ids = [(1, line.id, {
                    'raw_workorder_id': False,
                    'orig_rewo_id': self.id,
                    'qty_done': 1,
                    'company_id': line._get_production().company_id.id,
                    'lot_id': self.finished_lot_id,
                    'move_line_id': move_line_id,
                }) for line in self.raw_workorder_line_ids]
            reworkorder_lines = self.reworkorder_id._defaults_from_to_reworkorder_line().filtered(lambda rewol: rewol.move_line_id)
        elif not self.component_tracking and self.product_tracking == "serial":
            self.env['mrp.workorder.line'].create({
                    'product_id': self.product_id.id,
                    'product_uom_id': self.product_id.uom_id.id,
                    'orig_rewo_id': self.id,
                    'qty_done': 1,
                    'lot_id': self.finished_lot_id.id,
                    'move_line_id': move_line_id,
                })
            reworkorder_lines = self.reworkorder_id._defaults_from_to_reworkorder_line()

        # Need to update quality check in case of manual rework
        if not auto:
            # Unlink for bypass material registration
            if check_id.test_type == "register_consumed_materials":
                check_id.unlink()
            else:
                # Mark fail and assign finished lot to track
                check_id.do_fail()
                if self.finished_lot_id:
                    check_id.write({
                        'finished_lot_id': self.finished_lot_id.id
                    })

        # Update Rework Order for setting up default values
        self.reworkorder_id._defaults_from_finished_workorder_line(reworkorder_lines.sorted(
                key=lambda rewol: rewol.create_date, reverse=True
            ))
        self.reworkorder_id._change_quality_check(position=0)

        # Update current work order for next step
        self._apply_update_workorder_lines()
        self.write({'finished_lot_id': False, 'lot_id': False})
        rounding = self.product_uom_id.rounding
        if float_compare(self.qty_producing, 0, precision_rounding=rounding) > 0:
            self.with_context(rework_sequence=True)._create_checks()

        return True

    def do_fail(self):
        self.ensure_one()
        # Ensure that finished lot is available for auto record production from `_next` step
        if self.product_tracking != 'none' and not self.finished_lot_id:
            raise UserError(_('You should provide a lot for the final product !'))
        check_id = self.current_quality_check_id
        res = super(MrpWorkorder, self).do_fail()
        if self.check_ids:
            # Check if you can attribute the lot to the checks
            if (self.production_id.product_id.tracking != 'none') and self.finished_lot_id:
                self.check_ids.filtered(lambda check: not check.finished_lot_id).write({
                    'finished_lot_id': self.finished_lot_id.id
                })
        # Do Rework
        if check_id and check_id.point_id and check_id.point_id.rework_process == "auto":
            self.do_rework(auto=True)
        # Returning super redirect fail message
        return res

    def do_pass(self):
        self.ensure_one()
        # Ensure that finished lot is available for auto record production from `_next` step
        if self.product_tracking != 'none' and not self.finished_lot_id:
            raise UserError(_('You should provide a lot for the final product !'))
        return super(MrpWorkorder, self).do_pass()

    def _create_or_update_rework_finished_line(self):
        current_lot_lines = self.finished_reworkorder_line_ids.filtered(lambda line: line.lot_id == self.finished_lot_id)
        if not current_lot_lines:
            self.env['mrp.workorder.line'].create({
                'finished_reworkorder_id': self.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_id.uom_id.id,
                'lot_id': self.finished_lot_id.id,
                'qty_done': self.qty_producing,
                'company_id': self.production_id.company_id.id,
                'rework_state': "done",
            })
        else:
            current_lot_lines.qty_done += self.qty_producing

    def _defaults_from_workorder_lines(self, move, test_type):
        line = super(MrpWorkorder, self)._defaults_from_workorder_lines(move, test_type)
        if line.get('lot_id', False):
            line.pop('lot_id')
        return line

    def record_rework_production(self):
        if not self:
            return True

        self.ensure_one()
        prev_orig_move_line_id = self.orig_move_line_id
        prev_lot_id = self.finished_lot_id
        self._check_company()

        if self.product_tracking and self.product_tracking == "serial" and not self.finished_lot_id:
            raise UserError(_('You have to enter a serial number for product!'))

        if self.product_tracking and self.product_tracking == "serial" and self.finished_lot_id:
            related_rewol = self.production_id.workorder_ids.mapped('to_reworkorder_line_ids').filtered(
                    lambda rewol: self.finished_lot_id.id == rewol.lot_id.id and rewol.rework_state == "pending"
                )
            if not related_rewol:
                raise UserError(_('Serial number %s not available for rework!') % (self.finished_lot_id.name))
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

        # Transfer lot (if present) and quantity produced to a finished workorder line
        if self.product_tracking != 'none':
            self._create_or_update_rework_finished_line()

        # Update workorder quantity produced
        self.qty_produced += self.qty_producing

        # One a piece is produced, you can launch the next work order
        # self._start_nextworkorder()
        to_reworkorder_line_ids = self.production_id.workorder_ids.mapped('to_reworkorder_line_ids')
        rewol_to_update = to_reworkorder_line_ids.filtered(lambda rewol: rewol.lot_id.id == prev_lot_id.id)
        if prev_orig_move_line_id and prev_lot_id:
            rewol_to_update.write({
                    'move_line_id': False,
                    'rework_state': "done",
                })
        else:
            rewol_to_update.write({'rework_state': "done",})
        # Test if the production is done
        rounding = self.production_id.product_uom_id.rounding
        # Get to rework lines length
        if float_compare(self.qty_produced, self.qty_rework, precision_rounding=rounding) < 0:
            previous_wo = self.env['mrp.workorder']
            if self.product_tracking != 'none':
                previous_wo = self.env['mrp.workorder'].search([
                    ('next_work_order_id', '=', self.id)
                ])
            candidate_found_in_previous_wo = False

            if previous_wo:
                candidate_found_in_previous_wo = self._defaults_from_finished_workorder_line(previous_wo.finished_workorder_line_ids)
            if not candidate_found_in_previous_wo:
                # self is the first workorder
                self.qty_producing = self.qty_remaining
                self.finished_lot_id = False
                if self.product_tracking == 'serial':
                    self.qty_producing = 1

            self._apply_update_workorder_lines()
        else:
            self.qty_producing = 0
            # Save reworkorder as pending
            self.button_pending()
        return True

    def _create_checks(self):
        ''' @Overwrite to manage of changing quality check when put the
        quantity to the rework process
        : _change_quality_check: params(`goto`) -> currently created quality check
        '''
        for wo in self:

            # skip the reworkorder to stop creating quality checks
            if wo.is_reworkorder:
                continue

            # Track components which have a control point
            processed_move = self.env['stock.move']

            production = wo.production_id
            points = self.env['quality.point'].search([('operation_id', '=', wo.operation_id.id),
                                                       ('picking_type_id', '=', production.picking_type_id.id),
                                                       ('company_id', '=', wo.company_id.id),
                                                       '|', ('product_id', '=', production.product_id.id),
                                                       '&', ('product_id', '=', False), ('product_tmpl_id', '=', production.product_id.product_tmpl_id.id)])
            move_raw_ids = wo.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            move_finished_ids = wo.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            values_to_create = []
            for point in points:
                # Check if we need a quality control for this point
                if point.check_execute_now():
                    moves = self.env['stock.move']
                    values = {
                        'workorder_id': wo.id,
                        'point_id': point.id,
                        'team_id': point.team_id.id,
                        'company_id': wo.company_id.id,
                        'product_id': production.product_id.id,
                        # Two steps are from the same production
                        # if and only if the produced quantities at the time they were created are equal.
                        'finished_product_sequence': wo.qty_produced,
                    }
                    if point.test_type == 'register_byproducts':
                        moves = move_finished_ids.filtered(lambda m: m.product_id == point.component_id)
                    elif point.test_type == 'register_consumed_materials':
                        moves = move_raw_ids.filtered(lambda m: m.product_id == point.component_id)
                    else:
                        values_to_create.append(values)
                    # Create 'register ...' checks
                    for move in moves:
                        check_vals = values.copy()
                        check_vals.update(wo._defaults_from_workorder_lines(move, point.test_type))
                        values_to_create.append(check_vals)
                    processed_move |= moves

            # Generate quality checks associated with unreferenced components
            moves_without_check = ((move_raw_ids | move_finished_ids) - processed_move).filtered(lambda move: move.has_tracking != 'none')
            quality_team_id = self.env['quality.alert.team'].search([], limit=1).id
            for move in moves_without_check:
                values = {
                    'workorder_id': wo.id,
                    'product_id': production.product_id.id,
                    'company_id': wo.company_id.id,
                    'component_id': move.product_id.id,
                    'team_id': quality_team_id,
                    # Two steps are from the same production
                    # if and only if the produced quantities at the time they were created are equal.
                    'finished_product_sequence': wo.qty_produced,
                }
                if move in move_raw_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_consumed_materials')
                if move in move_finished_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_byproducts')
                values.update({'test_type_id': test_type.id})
                values.update(wo._defaults_from_workorder_lines(move, test_type.technical_name))
                values_to_create.append(values)

            current_check_id = self.env['quality.check'].create(values_to_create)
            # Set default quality_check
            wo.skip_completed_checks = False

            # go to next (currently created) quality check when put the qualtity in rework process
            if self._context.get('rework_sequence', False):
                wo._change_quality_check(goto=current_check_id.id)
            else:
                wo._change_quality_check(position=0)

    def record_production(self):
        finished_lot_id = self.finished_lot_id
        prev_orig_move_line_id = self.orig_move_line_id

        if not self.is_reworkorder and self.has_rework and not self.component_tracking:
            raise UserError(_("Rework of this product is currently in progress!"))

        if self.is_reworkorder:
            self = self.with_context(reworkorder_id=self.id)
            return self.record_rework_production()
        res = super(MrpWorkorder, self).record_production()
        # check if final WO then done rework here
        if self.is_last_unfinished_wo and self.state == "done":
            reworkorder_id = self.production_id.workorder_ids.filtered(lambda workorder: workorder.is_reworkorder)
            # check if reworkorder is not processed then update it's planned dates
            if reworkorder_id and reworkorder_id.state == "pending":
                start_date = datetime.now()
                reworkorder_id.write({
                    'date_start': start_date,
                    'date_planned_start': start_date,
                })
            reworkorder_id.button_finish()
        return res

    def button_start(self):
        if self.is_reworkorder and not self._defaults_from_to_reworkorder_line().filtered(
                        lambda rewol: rewol.lot_id and rewol.rework_state == "pending"
                    ):
            raise Warning(_("No quantities available for rework."))
        return super(MrpWorkorder, self).button_start()

    def _assign_component_lot_to_finish_lot(self):
        self.ensure_one()
        # Search for candidate lot depends on component lot
        candidate_lot = self.env['stock.production.lot'].search([
                ('name', '=', self.lot_id.name),
                ('product_id', '=', self.product_id.id),
                ('company_id', '=', self.company_id.id),
            ])

        # Check lot has quants available
        get_available_quantity = lambda lot: self.env['stock.quant']._get_available_quantity(
                self.product_id,
                self.production_id.location_dest_id,
                lot_id=lot,
                strict=True
            )

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        def _check_candidate_availability(candidate_lot):
            available_quantity = get_available_quantity(candidate_lot)
            if float_compare(available_quantity, 0, precision_digits=precision) <= 0:
                self.finished_lot_id = candidate_lot.id
            else:
                raise UserError(_("SN {} of product {} is already available in the system with {} {}.".format(
                        candidate_lot.name,
                        self.product_id.display_name,
                        available_quantity,
                        self.product_uom_id.name,
                    )))

        if self.component_tracking == "serial" and self.lot_id and self.qty_done != 0:
            if not self.finished_lot_id:
                # Try search if available then no need to create
                if candidate_lot:
                    _check_candidate_availability(candidate_lot)
                else:
                    finished_lot_id = self.env['stock.production.lot'].create({
                            'name': self.lot_id.name,
                            'product_id': self.product_id.id,
                            'company_id': self.company_id.id,
                        })
                    self.write({
                            'finished_lot_id': finished_lot_id.id,
                            'created_finished_lot_ids': [(4, finished_lot_id.id)],
                        })
            else:
                if candidate_lot:
                    _check_candidate_availability(candidate_lot)
                else:
                    self.finished_lot_id.write({"name": self.lot_id.name})
        return True

    def _next(self, continue_production=False):
        auto_record = False
        prev_quality_check_id = self.current_quality_check_id
        if self.has_rework:
            raise UserError(_("Rework of this component is currently in progress!"))
        if self.component_tracking == "serial" and self.product_tracking == "serial":
            self._assign_component_lot_to_finish_lot()
        # super calling: return fail message if quality point available and not auto record production
        res = super(MrpWorkorder, self)._next(continue_production=continue_production)
        if self.is_user_working or self.is_last_step or not self.skipped_check_ids or not self.is_last_lot:
            auto_record = True
            if prev_quality_check_id and prev_quality_check_id.quality_state == 'fail':
                auto_record = False

        if auto_record and not continue_production:
            # check is last quantity to process then `do_finish` for redirect next WO
            if self.is_last_lot:
                res = self.do_finish()
            else:
                res = self.record_production()
        return res

    def button_show_reworkorder(self):
        self.ensure_one()

        if not self.reworkorder_id:
            raise Warning("Rework Workorder is not available for this workorder.")

        if self.env.context.get('active_model') == self._name:
            action = self.env.ref('mrp.action_mrp_workorder_production_specific').read()[0]
            action['context'] = {'search_default_production_id': self.production_id.id}
            action['target'] = 'main'
        else:
            # workorder tablet view action should redirect to the same tablet view with same workcenter when WO mark as done.
            action = self.env.ref('mrp_workorder.mrp_workorder_action_tablet').read()[0]
            action['context'] = {
                'form_view_initial_mode': 'edit',
                'no_breadcrumbs': True,
                'search_default_workcenter_id': self.reworkorder_id.workcenter_id.id
            }
        action['domain'] = [('state', 'not in', ['done', 'cancel', 'pending'])]
        return action

    def action_info(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_extended.mrp_workorder_view_form_tablet_info').id, 'form']],
            'name': _('Information'),
            'target': 'new',
            'res_id': self.id,
        }

    def _scan_action_component(self, barcode, lot):
        if lot:
            # Check is corresponding lot is reserved for production or not
            available_component_lots = self._get_unused_component_lots()

            if available_component_lots and (lot.id not in available_component_lots.ids):
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Corresponding component '%(product)s' of barcode '%(barcode)s' doesn\'t available or already consumed!" % {
                                'product': self.component_id.display_name,
                                'barcode': barcode,
                            })
                    }
                }

            # Check is corresponding lot is currently in rework or not
            corresponding_rework_move_line = self.to_reworkorder_line_ids.mapped('move_line_id').filtered(
                    lambda ml: lot and ml.lot_id.id == lot.id
                )

            if corresponding_rework_move_line:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Corresponding product %s of barcode %s is currently in rework!\
                            You can only process once it will be processed from rework station." % (
                                corresponding_rework_move_line.product_id.display_name,
                                barcode,
                            ))
                    }
                }

            self.lot_id = lot
        else:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _("The barcode '%(barcode)s' doesn\'t correspond to LN/SN for component '%(product)s'." % {
                            'barcode': barcode,
                            'product': self.component_id.display_name
                        })
                }
            }

    def _scan_action_finish(self, barcode, lot):
        if lot:
            if not self.is_reworkorder:
                previously_finished_lots = self._get_previously_finished_lots()
                if previously_finished_lots and not (lot.id in previously_finished_lots.ids):
                    return {
                        'warning': {
                            'title': _("Warning"),
                            'message': _("Corresponding product %s of barcode %s is not finished yet in previous workorder %s!" % (
                                    self.product_id.display_name,
                                    barcode,
                                    previous_wo.display_name
                                )
                            )
                        }
                    }
            else:
                reworkorder_lines = self._origin._defaults_from_to_reworkorder_line()
                if lot.id not in reworkorder_lines.mapped('lot_id').ids:
                    return {
                        'warning': {
                            'title': _("Warning"),
                            'message': _("The corresponding product '%(product)s' of barcode '%(barcode)s' doesn\'t available for rework!" % {
                                    'product': self.product_id.display_name,
                                    'barcode': barcode,
                                })
                        }
                    }

            self.finished_lot_id = lot
        else:
            return {
                'warning': {
                    'title': _("Warning"),
                    'message': _("The barcode '%(barcode)s' doesn\'t correspond to LN/SN for product '%(product)s'." % {
                            'barcode': barcode,
                            'product': self.product_id.display_name
                        })
                }
            }

    def on_barcode_scanned(self, barcode):
        # qty_done field for serial numbers is fixed
        if self.component_tracking != 'serial':
            if not self.lot_id:
                # not scanned yet
                self.qty_done = 1
            elif self.lot_id.name == barcode:
                self.qty_done += 1
            else:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("You are using components from another lot. \nPlease validate the components from the first lot before using another lot.")
                    }
                }

        # <function: return corresponding lot for finish or component product>
        get_corresponding_lot = lambda product: self.env['stock.production.lot'].search([
                ('name', '=', barcode), ('product_id', '=', product.id)
            ])

        _scan_step = not self.workcenter_id.use_create_lot_from_comp_lot and "finish" or "component"

        # get corresponding finish/component lot by barcode
        finish_lot = get_corresponding_lot(self.product_id)
        component_lot = get_corresponding_lot(self.component_id)

        # update the `_scan_step` depends on corresponding lot and current data
        if _scan_step == "finish" and self.production_id.product_id.tracking and self.production_id.product_id.tracking != 'none':
            if self.finished_lot_id and not finish_lot and component_lot:
                _scan_step = "component"
        elif _scan_step == "component" and self.component_tracking and self.component_tracking != 'none':
            if self.lot_id and not component_lot and finish_lot:
                _scan_step = "finish"

        # get corresponding lot based on scan step
        corresponding_lot = finish_lot if _scan_step == "finish" else component_lot
        return getattr(self, '_scan_action_%s' % _scan_step)(barcode, corresponding_lot)


class MrpWorkorderLine(models.Model):
    _inherit = 'mrp.workorder.line'

    def _compute_rework_title(self):
        for line in self:
            line.rework_title = 'Rework of "{}"'.format(line.product_id.name)
            line.rework_result = 'Reworked {} - {}, {} {}'.format(
                    line.product_id.name,
                    line.lot_id.name,
                    line.qty_done,
                    line.product_uom_id.name
                )

    rework_title = fields.Char('Title', compute='_compute_rework_title')
    rework_result = fields.Char('Result', compute='_compute_rework_title')
    rework_state = fields.Selection([
        ('pending', "To Rework"),
        ('done', "Done")], string="Rework Status", default="pending")
    orig_rewo_id = fields.Many2one('mrp.workorder', 'Origin Product for Re-Workorder',
        ondelete='cascade')
    finished_reworkorder_id = fields.Many2one('mrp.workorder', 'Finished Re-Workorder',
        ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', string="Related Move Line")

    def _get_production(self):
        production_id = super(MrpWorkorderLine, self)._get_production()
        if not production_id and self.finished_reworkorder_id:
            production_id = self.finished_reworkorder_id.production_id
        elif not production_id and self.orig_rewo_id:
            production_id = self.orig_rewo_id.production_id
        return production_id
