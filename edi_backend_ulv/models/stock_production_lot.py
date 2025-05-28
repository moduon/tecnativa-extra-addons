#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
import logging
from datetime import timedelta

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    last_move_line_id = fields.Many2one(
        comodel_name="stock.move.line",
        compute="_compute_last_move_line_id",
    )
    last_inventory_move_id = fields.Many2one(
        comodel_name="stock.move",
        compute="_compute_last_inventory_move_id",
    )
    unilever_move_type = fields.Selection(
        [
            ("C", "Entrega al cliente"),
            ("E", "Recogida del cliente"),
            ("A", "Alta del medio"),
            ("B", "Baja del medio"),
            ("X", "Cambio de concesión"),
            ("R", "Recuperada"),
        ],
        compute="_compute_unilever_move_type",
    )
    unilever_low_reason = fields.Selection(
        [
            ("D", "Desguace"),
            ("V", "Venta"),
            ("P", "Pérdida"),
            ("O", "Donación"),
            ("R", "Robo"),
            ("E", "Error de gestion (No se enviará a Unilever)"),
        ],
        string="UL low reason",
    )
    ul_date_last_verification = fields.Date(string="Last verification")
    ul_date_recount = fields.Date(compute="_compute_ul_date_recount")
    change_dealer = fields.Boolean()

    def _compute_last_move_line_id(self):
        for lot in self:
            logger.info(f"LOTE LAST MOVE LINE: {lot.name}")
            move_line = self.env["stock.move.line"].search(
                [
                    ("product_id", "=", lot.product_id.id),
                    ("lot_id", "=", lot.id),
                    ("state", "=", "done"),
                    ("location_dest_id.scrap_location", "=", False),
                    ("location_dest_id.usage", "!=", "inventory"),
                    ("location_id.usage", "!=", "inventory"),
                    "|",
                    "|",
                    "&",
                    ("location_id.usage", "=", "internal"),
                    ("location_dest_id.usage", "!=", "internal"),
                    "&",
                    ("location_id.usage", "!=", "internal"),
                    ("location_dest_id.usage", "=", "internal"),
                    "&",
                    ("location_id.usage", "!=", "internal"),
                    ("location_dest_id.usage", "!=", "internal"),
                ],
                order="id DESC",
                limit=1,
            )
            lot.last_move_line_id = move_line

    def _compute_last_inventory_move_id(self):
        for lot in self:
            logger.info(f"LOTE INVENTORY: {lot.name}")
            line = self.env["stock.move.line"].search(
                [
                    ("move_id.is_inventory", "=", True),
                    ("product_id", "=", lot.product_id.id),
                    ("lot_id", "=", lot.id),
                    ("state", "=", "done"),
                ],
                order="id DESC",
                limit=1,
            )
            lot.last_inventory_move_id = line.move_id

    def _compute_unilever_move_type(self):
        for lot in self:
            if lot.change_dealer:
                lot.unilever_move_type = "X"
                continue
            if lot.unilever_low_reason:
                lot.unilever_move_type = "B"
                continue
            move_line = lot.last_move_line_id
            if move_line.location_dest_id.usage == "customer":
                lot.unilever_move_type = "C"
            elif move_line.location_id.usage == "customer":
                lot.unilever_move_type = "E"
            elif move_line.location_dest_id.usage == "supplier":
                lot.unilever_move_type = "B"
            elif move_line.location_id.usage == "supplier":
                lot.unilever_move_type = "A"
            else:
                lot.unilever_move_type = False

    def _compute_ul_date_recount(self):
        for lot in self:
            lot.ul_date_recount = False
            if (
                lot.ul_date_last_verification
                and lot.last_inventory_move_id.date
                and lot.ul_date_last_verification
                > fields.Date.to_date(lot.last_inventory_move_id.date)
            ):
                lot.ul_date_recount = lot.ul_date_last_verification
            elif lot.ul_date_last_verification and not lot.last_inventory_move_id.date:
                lot.ul_date_recount = lot.ul_date_last_verification
            elif lot.last_inventory_move_id.date:
                lot.ul_date_recount = lot.last_inventory_move_id.date
            else:
                lot.ul_date_recount = self.env.context.get(
                    "last_inventory_move_date", False
                )

    def button_unilever_date_register(self):
        self.ul_date_last_verification = fields.Date.today()

    # Reporting bussiness methods
    @api.model
    def get_recount_pending_freezers(self, docids=None):
        """Invoked from:
        _get_report_action in stock.production.lot (this file),
        _get_report_values in report.edi_backend_ulv.recount_pending_freezers,
        generate_xlsx_report in report.edi_backend_ulv.recount_pending_freezers_xlsx

        docids is passed when it is invoked from report.edi_backend_ulv.* models
        """
        date_recount = fields.Datetime.now() - timedelta(
            days=self.env.company.no_recount_days_limit
        )
        domain = [
            ("product_id.categ_id.is_unilever_mef", "=", True),
            ("unilever_low_reason", "=", False),
            ("change_dealer", "=", False),
            "|",
            ("ul_date_last_verification", "<", date_recount),
            ("ul_date_last_verification", "=", False),
        ]
        if docids:
            domain = [("id", "in", docids)] + domain
        return self.search(domain).filtered(lambda r: r.unilever_move_type == "C")

    @api.model
    def _get_report_action(self, report):
        records = self.get_recount_pending_freezers()
        data = {"docids": records.ids, "server_action": True}
        logger.info(f"LOTES A PROCESAR: {len(records)}")
        return report.report_action(records.ids, data=data)

    def print_recount_pending_freezers_report(self):
        report = self.env.ref(
            "edi_backend_ulv.report_unilever_recount_pending_freezers"
        )
        return self._get_report_action(report)

    def print_recount_pending_freezers_xlsx_report(self):
        report = self.env.ref(
            "edi_backend_ulv.report_unilever_recount_pending_freezers_xlsx"
        )
        return self._get_report_action(report)
