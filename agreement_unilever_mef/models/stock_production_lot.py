#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import _, models
from odoo.exceptions import UserError


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    def action_agreement_unilever_mef(self):
        self.ensure_one()
        agreements = self.env["agreement"].search(
            [("domain", "=", "unilever_mef"), ("mef_lot_id", "=", self.id)]
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
                "default_mef_lot_id": self.id,
            }
        )
        action["context"] = ctx
        return action
