# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import xlrd
import base64
from datetime import datetime
from odoo.exceptions import Warning
from odoo import models, fields, _


class MrpWorkorderImportXlsResult(models.TransientModel):
    _name = "mrp.workorder.import.xls_result"
    _description = "Mrp Workorder Import Excel Result"
    _rec_name = "file"

    file = fields.Binary("Test Result Excel File", required=True,
                         help="Report file to import test results and process workorder.")

    def process_import_test_result(self):
        workorder = self._context.get('active_id', False) and self.env["mrp.workorder"].browse(self._context.get('active_id')) or False
        if not workorder:
            raise Warning(_("Workorder not found to process test result excel file."))

        try:
            workbook = xlrd.open_workbook(file_contents=base64.decodestring(self.file))
        except Exception as e:
            raise Warning(_(e))
        last_process_date = False
        for sheet in workbook.sheets():
            for row in range(sheet.nrows):
                if row == 2:
                    if sheet.cell(row, 1).value.strip().lower() != 'asset no.':
                        raise Warning(_("Invalid File Format. File should contain 'Asset No.' in Column B."))
                    if sheet.cell(row, 31).value.strip().lower() != 'sta':
                        raise Warning(_("Invalid File Format. File should contain 'STA' in Column AF."))
                    if sheet.cell(row, 32).value.strip().lower() != 'crp':
                        raise Warning(_("Invalid File Format. File should contain 'CRP' in Column AG."))
                    if sheet.cell(row, 33).value.strip().lower() != 'votage test':
                        raise Warning(_("Invalid File Format. File should contain 'Votage test' in Column AH."))
                    if sheet.cell(row, 34).value.strip().lower() != 'result':
                        raise Warning(_("Invalid File Format. File should contain 'Result' in column AI."))
                if row < 5:
                    continue
                componenet_ref = sheet.cell(row, 1).value
                finish_ref = sheet.cell(row, 2).value
                if workorder.lot_id and workorder.lot_id.name == componenet_ref:
                    if sheet.cell(row, 34).value == "F":
                        workorder.do_rework()
                    elif sheet.cell(row, 34).value == "P":
                        if workorder.current_quality_check_id and workorder.current_quality_check_id.point_id:
                            workorder.check_ids.filtered(lambda check: check.product_id.id == workorder.current_quality_check_id.product_id.id)
                            workorder.do_pass()
                        else:
                            workorder._next()
                continue

                if workorder.product_id and workorder.product_id.default_code and workorder.product_id.default_code == ref:
                    sta = "pass"
                    if sheet.cell(row, 31).value != "P":
                        sta = "fail"

                    crp = "pass"
                    if sheet.cell(row, 32).value != "P":
                        crp = "fail"

                    votage_test = "pass"
                    if sheet.cell(row, 33).value != "P":
                        votage_test = "fail"

                    result = "pass"
                    if sheet.cell(row, 34).value != "P":
                        result = "fail"

                    workorder.write({
                        'sta': sta,
                        'crp': crp,
                        'votage_test': votage_test,
                        'result': result,
                    })
                    last_process_date = datetime.now().date()
        if workorder.result == "fail":
            workorder.do_rework()
        elif workorder.result == "pass":
            if workorder.current_quality_check_id and workorder.current_quality_check_id.point_id and workorder.current_quality_check_id.point_id.test_type_id.id == self.env.ref("quality_control.test_type_passfail").id:
                workorder.do_pass()
            elif workorder.current_quality_check_id and workorder.current_quality_check_id.point_id and workorder.current_quality_check_id.point_id.test_type_id.id != self.env.ref("quality_control.test_type_passfail").id:
                raise Warning(_("Only Pass-Fail quality check is supported in this version."))

        if last_process_date:
            workorder.write({
                "last_test_import_date": last_process_date,
                "last_test_import_user": self.env.user.id,
            })
        else:
            workorder.button_pending()
        return True
