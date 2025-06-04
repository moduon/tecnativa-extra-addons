#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import _, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_fresh_asset(self):
        self.ensure_one()
        location_customer = self.env.ref("stock.stock_location_customers")
        moves = self.env["stock.move"].search(
            [
                ("state", "=", "done"),
                ("picking_id.partner_id", "=", self.id),
                ("product_id.categ_id.is_unilever_mef", "=", True),
                ("location_dest_id", "=", location_customer.id),
            ],
            order="date DESC",
        )
        lot_list = []
        for move in moves:
            for line in move.move_line_ids:
                # Buscar el ultimo movimiento de este lote para saber donde
                # está o si está en otro cliente.
                domain = [
                    ("state", "=", "done"),
                    ("lot_id", "=", line.lot_id.id),
                ]
                last_move_line = self.env["stock.move.line"].search(
                    domain, limit=1, order="date DESC"
                )
                if (
                    last_move_line.location_dest_id != location_customer
                    or last_move_line.picking_id.partner_id != self
                ):
                    continue
                lot_id = line.lot_id.id
                if lot_id in lot_list:
                    continue
                lot_list.append(lot_id)
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_production_lot_form"
        )
        action["domain"] = [("id", "in", lot_list)]
        return action

    def action_agreement_unilever_mef(self):
        self.ensure_one()
        agreements = self.env["agreement"].search(
            [("domain", "=", "unilever_mef"), ("partner_id", "=", self.id)]
        )
        if not agreements:
            raise UserError(_("No agreements found!"))

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "agreement.agreement_action"
        )
        action["domain"] = [("id", "in", agreements.ids)]
        ctx = self.env.context.copy()
        ctx.update(
            {
                "default_agreement_type_id": self.env.ref(
                    "agreement_unilever_mef.agreement_type_mef"
                ).id,
                "default_partner_id": self.id,
            }
        )
        action["context"] = ctx
        return action
