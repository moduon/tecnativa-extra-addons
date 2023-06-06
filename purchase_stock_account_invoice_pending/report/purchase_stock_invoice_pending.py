# Copyright 2022 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.tools.float_utils import float_is_zero


class InvoicePickingReport(models.AbstractModel):
    _name = "report.purchase_stock_account_invoice_pending.purchase_pending"
    _inherit = "report.report_xlsx.abstract"
    _description = "Abstract Report to print purchase stock account invoice pending"

    @api.model
    def _get_report_data(self, data):
        PurchaseOrder = self.env["purchase.order"]
        PurchaseOrderLine = self.env["purchase.order.line"]
        report_data = {}
        # Prefetch records
        orders = PurchaseOrder.browse([r["order_id"] for r in data["recs_to_print"]])
        lines = PurchaseOrderLine.browse([r["id"] for r in data["recs_to_print"]])
        for vals in data["recs_to_print"]:
            po = orders.browse(vals["order_id"])
            if po not in report_data:
                report_data[po] = {
                    "amount_pending": 0.0,
                }
            po_line = lines.browse(vals["id"])
            price_unit = (
                po_line.price_subtotal / po_line.product_uom_qty
                if po_line.product_uom_qty
                else po_line.price_unit
            )
            # ERROR USING move._get_price_unit
            report_data[po]["amount_pending"] += price_unit * (
                vals["moves_qty"] - vals["invoiced_qty"]
            )
        return sorted(
            report_data.items(),
            key=lambda kv: (
                kv[0]["date_approve"] or kv[0]["date_order"],
                kv[0]["name"],
            ),
        )

    @api.model
    def _set_workbook_data(self, workbook, report_data):
        subheader_format = workbook.add_format(
            {"bold": 1, "border": 1, "align": "center", "valign": "vjustify"}
        )
        decimal_format = workbook.add_format({"num_format": "#,##0.00"})
        date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})
        sheet = workbook.add_worksheet(_("Recepciones no facturadas"))

        row_index = 0
        next_col = 0
        sheet.write(row_index, next_col, _("Fecha pedido"), subheader_format)
        sheet.set_column(next_col, next_col, 14, date_format)
        next_col += 1
        sheet.write(row_index, next_col, _("Referencia PO"), subheader_format)
        sheet.set_column(next_col, next_col, 16)
        next_col += 1
        sheet.write(row_index, next_col, _("Proveedor"), subheader_format)
        sheet.set_column(next_col, next_col, 60)
        next_col += 1
        sheet.write(row_index, next_col, _("Base imponible total"), subheader_format)
        sheet.set_column(next_col, next_col, 25, decimal_format)
        next_col += 1
        sheet.write(row_index, next_col, _("Pendiente de facturar"), subheader_format)
        sheet.set_column(next_col, next_col, 25, decimal_format)

        # Rows
        for po, vals in report_data:
            if float_is_zero(vals["amount_pending"], precision_digits=2):
                continue
            row_index += 1
            sheet.write(row_index, 0, po.date_approve or po.date_order)
            share_url = po.get_base_url() + po._get_share_url(
                redirect=True, share_token=False
            )
            sheet.write_url(row_index, 1, share_url, string=po.name)
            sheet.write(row_index, 2, po.partner_id.name)
            sheet.write(row_index, 3, po.amount_untaxed)
            sheet.write(row_index, 4, vals["amount_pending"])

    @api.model
    def generate_xlsx_report(self, workbook, data, docs):
        report_data = self._get_report_data(data)
        self._set_workbook_data(workbook, report_data)
