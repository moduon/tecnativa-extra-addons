# Copyright 2021 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ReportRecountPendingFreezersXLSX(models.AbstractModel):
    _name = "report.edi_backend_ulv.recount_pending_freezers_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Unilever recount pending freezers xlsx"

    @api.model
    def _get_report_data(self, lots):
        report_data = []
        for lot in lots:
            partner = lot.last_move_line_id.move_id.partner_id
            report_data.append(
                {
                    "Matrícula": lot.name,
                    "Nombre Producto": lot.product_id.name,
                    "Cliente": partner.display_name,
                    "Provincia": partner.state_id.name,
                    "Ciudad": partner.city,
                    "Comercial del cliente": partner.user_id.name,
                    "Última fecha de recuento": lot.ul_date_recount,
                }
            )
        return report_data

    @api.model
    def _set_workbook_data(self, workbook, report_data):
        sheet = workbook.add_worksheet("Report")
        columns_list = [
            "Matrícula",
            "Nombre Producto",
            "Cliente",
            "Provincia",
            "Ciudad",
            "Comercial del cliente",
            "Última fecha de recuento",
        ]
        # Cell formats
        bold = workbook.add_format({"bold": True})
        format_map = {
            "Última fecha de recuento": workbook.add_format(
                {"num_format": "dd/mm/yyyy"}
            )
        }
        # Tracking the maximum width to simulate AutoFit at the end
        col_width = {}
        # Header
        row_index = 0
        for col_index, col in enumerate(columns_list):
            col_width[col] = len(col)
            sheet.write(row_index, col_index, col, bold)
        # Rows
        for line_data in report_data:
            row_index += 1
            for col_index, col in enumerate(columns_list):
                col_width[col] = max(col_width[col], len(str(line_data.get(col, ""))))
                cell_value = line_data.get(col, None) or None
                cell_format = format_map.get(col, None)
                sheet.write(row_index, col_index, cell_value, cell_format)
        # Set maximun width to every column to simulate AutoFit
        for col_index, col in enumerate(columns_list):
            sheet.set_column(col_index, col_index, col_width[col])

    @api.model
    def generate_xlsx_report(self, workbook, data, docs):
        # If data.get("server_action") is True, the report is requested
        # from a server action (invoked from a menu option) and the
        # docids ARE ALREADY CORRECTLY FILTERED, else the it is
        # requested generated from a view of 'Lots/Serial Numbers'
        if data.get("server_action"):
            docs_to_print = docs
        else:
            doc_obj = self.env["stock.production.lot"]
            docs_to_print = doc_obj.get_recount_pending_freezers(docs.ids)
        report_data = self._get_report_data(docs_to_print)
        self._set_workbook_data(workbook, report_data)
