# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import xlrd
import base64
from datetime import datetime
from odoo.exceptions import Warning
from odoo.tools import float_compare
from odoo import models, fields, _


class MrpWorkorderImportXlsResult(models.TransientModel):
    _name = "mrp.workorder.import.xls_result"
    _description = "Mrp Workorder Import Excel Result"
    _rec_name = "file"

    file = fields.Binary(string="Test Result Excel File", required=True,
        help="Report file to import test results and process workorder.")

    def process_import_test_result(self):
        MrpWorkorder = self.env["mrp.workorder"]
        workorder = self._context.get('active_id', False) and MrpWorkorder.browse(self._context.get('active_id')) or False
        if not workorder:
            raise Warning(_("Workorder not found to process test result excel file."))
        try:
            workbook = xlrd.open_workbook(file_contents=base64.decodestring(self.file))
        except Exception as e:
            raise Warning(_(e))

        values = list()
        # ensure one 'last_qty_to_process'
        last_qty_to_process = False
        for sheet in workbook.sheets():
            for row in range(sheet.nrows):
                if row < 5:
                    continue

                final_result = True
                check_id = workorder.current_quality_check_id
                has_component_track = (check_id and\
                    workorder.component_tracking and\
                    workorder.component_tracking == "serial")

                component_lot_ref = sheet.cell(row, 1).value
                finish_lot_ref = sheet.cell(row, 2).value
                # get finished lots
                previously_finished_lots = workorder._get_previously_finished_lots()
                # match SN reference with `sheet.cell(row, 2).value`
                corresponding_lot_id = previously_finished_lots.filtered(lambda lot: lot.name == finish_lot_ref)
                if not has_component_track and workorder.product_tracking and workorder.product_tracking == "serial" and corresponding_lot_id:
                    # check if corresponding SN is already processed then bypass it.
                    if corresponding_lot_id in (workorder.finished_workorder_line_ids + workorder.to_reworkorder_line_ids.filtered(lambda rewol: rewol.rework_state != "done")).mapped('lot_id'):
                        continue
                    workorder.finished_lot_id = corresponding_lot_id.id
                    if sheet.cell(row, 34).value == "F":
                        # do rework/fail
                        final_result = False
                        workorder.do_rework()
                        if check_id:
                            workorder.do_fail()
                    elif sheet.cell(row, 34).value == "P":
                        # do process/pass
                        final_result = True
                        # Check if final quantity then process it after updating test result values
                        rounding = workorder.production_id.product_uom_id.rounding
                        if float_compare((workorder.qty_produced + 1.0), workorder.production_id.product_qty, precision_rounding=rounding) < 0:
                            if check_id:
                                workorder.do_pass()
                            workorder.record_production()
                        else:
                            last_qty_to_process = True

                    # Prepare values to write test results
                    values.append((0, 0, {
                        'component_lot_ref': component_lot_ref,
                        'finish_lot_ref': finish_lot_ref,
                        'workorder_id': workorder.id,
                        'sta': sheet.cell(row, 31).value != "P" and "fail" or "pass",
                        'crp': sheet.cell(row, 32).value != "P" and "fail" or "pass",
                        'votage_test': sheet.cell(row, 33).value != "P" and "fail" or "pass",
                        'result': final_result and "pass" or "fail",
                        'quality_check_id': check_id and check_id.id or False
                    }))

                else:
                    continue

        workorder.write({
            'last_test_import_date': fields.Datetime.now(),
            'last_test_import_user': self.env.user.id,
            'excel_test_result_ids': values
        })

        if last_qty_to_process:
            if not workorder.component_tracking and workorder.product_tracking and workorder.product_tracking == "serial":
                if workorder.current_quality_check_id:
                    workorder.do_pass()
                return workorder.record_production()
            workorder._next()

        return True
