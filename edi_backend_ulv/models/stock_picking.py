#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = ["stock.picking", "edi.backend.mixin"]
    _name = "stock.picking"

    no_charge = fields.Boolean(string="No charge")
    is_return = fields.Boolean(compute="_compute_is_return")
    unilever_invoice_refund_line_ids = fields.One2many(
        comodel_name="unilever.invoice.refund.line",
        inverse_name="picking_id",
        string="Unilever invoice refund lines",
        groups="account.group_account_invoice",
    )

    def _compute_is_return(self):
        for picking in self:
            picking.is_return = any(
                x.origin_returned_move_id for x in picking.move_lines
            )

    def action_ulv_communication_history(self):
        """Try to open the communication history where any of picking moves was send to
        Unilever
        """
        self.ensure_one()
        CommunicationHistory = self.env["edi.backend.communication.history"]
        history_backend = CommunicationHistory.browse()
        history_backends = self.env["edi.backend.communication.history"].search(
            [("create_date", ">=", self.date_done)]
        )
        for history in history_backends:
            history_move_set = set(json.loads(history.applied_records))
            picking_move_set = set(self.move_lines.ids)
            if history_move_set & picking_move_set:
                history_backend = history
                break
        if history_backend:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "base_edi_backend.action_edi_backend_communication_history"
            )
            action["domain"] = [("id", "in", history_backend.ids)]
            return action
        else:
            raise UserError(
                _("There is no file sent to Unilever containing" " this delivery slip")
            )
