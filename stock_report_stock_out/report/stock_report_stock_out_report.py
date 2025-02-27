# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import api, models
from odoo.tools.float_utils import float_compare, float_is_zero


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

    @api.model
    def _get_undelivered_moves(self, moves):
        """
        Sección 1 - Productos No entregados
        Productos que cumplen la condición:
            1. Cantidad demandada > 0 AND Cantidad entregada = 0
        """
        undelivered_moves = moves.filtered(
            lambda sm: float_is_zero(
                sm.quantity_done, precision_rounding=sm.product_uom.rounding
            )
            and float_compare(
                sm.product_uom_qty,
                sm.sale_line_id.product_uom_qty,
                precision_rounding=sm.product_uom.rounding,
            )
            == 0
            # and sm.product_uom_qty == sm.sale_line_id.product_uom_qty
            and sm.product_uom_qty > 0.0
        )
        return undelivered_moves

    @api.model
    def _get_partial_delivered_moves(self, moves):
        """
        Sección 2 - Entregado menos del XX% (incluir el XX% en el texto del informe)
        Productos que cumplen 2 condiciones
        1. Cantidad demandada > 0
        2. La cantidad entregada es menor del XX% de la cantidad demandada
            a. Ej xx=90: si piden 10 y entregamos 9, NO debe aparecer
            b. Ej xx=90: si piden 10 y entregamos 5, SI debe aparecer
        """
        partial_moves = self.env["stock.move"].browse()
        undelivered_moves = moves.filtered(
            lambda sm: float_is_zero(
                sm.quantity_done, precision_rounding=sm.product_uom.rounding
            )
            and float_compare(
                sm.product_uom_qty,
                sm.sale_line_id.product_uom_qty,
                precision_rounding=sm.product_uom.rounding,
            )
            != 0
            # and sm.product_uom_qty != sm.sale_line_id.product_uom_qty
            and sm.product_uom_qty > 0.0
        )
        for move in undelivered_moves:
            initial_demand = move.sale_line_id.product_uom_qty
            if initial_demand:
                percent_limit = (
                    move.product_id.product_tmpl_id.get_stock_out_tolerance_percentage()
                )
                # if move.product_uom_qty > initial_demand * percent_limit:
                if (
                    float_compare(
                        move.product_uom_qty,
                        initial_demand * percent_limit,
                        precision_rounding=move.product_uom.rounding,
                    )
                    == 1
                ):
                    partial_moves += move
        return partial_moves

    @api.model
    def _get_moves_dic(self, moves):
        undelivered_moves = self._get_undelivered_moves(moves)
        partial_delivered_moves = self._get_partial_delivered_moves(
            moves - undelivered_moves
        )
        product_dic = self._get_product_summary(
            undelivered_moves + partial_delivered_moves
        )
        moves_dic = {
            "undelivered_moves": undelivered_moves,
            "partial_delivered_moves": partial_delivered_moves,
            "product_dic": product_dic,
        }
        return moves_dic

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
            "moves_dic": self._get_moves_dic(moves),
        }
        return docargs
