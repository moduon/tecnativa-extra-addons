# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import models


class ReportStockReportStockOut(models.AbstractModel):
    _name = "report.stock_report_stock_out.report_stock_out"
    _description = "Report stock out abstract model"

    def _get_product_summary(self, moves):
        product_dic = defaultdict(
            lambda: {"partners": self.env["res.partner"], "quantity": 0.0}
        )
        for move in moves:
            product_dic[move.product_id]["partners"] |= move.picking_id.partner_id
            product_dic[move.product_id]["quantity"] += move.product_uom_qty
        return product_dic

    def _get_report_values(self, docids, data=None):
        report_name = "stock_report_stock_out.report_stock_out"
        report_obj = self.env["ir.actions.report"]
        report = report_obj._get_report_from_name(report_name)
        if "doc_ids" in data:
            doc_ids = data["doc_ids"]
        else:
            doc_ids = self.env.context.get("doc_ids")
        moves = self.env[report.model].browse(doc_ids)
        docargs = {
            "doc_ids": moves.ids,
            "doc_model": report.model,
            "docs": moves,
            "product_dic": self._get_product_summary(moves),
        }
        return docargs
