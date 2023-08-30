# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class ResPartner(models.Model):

    _inherit = "res.partner"

    def action_open_owner_quants(self):
        domain = [("owner_id", "child_of", self.ids)]
        ctx = dict(self.env.context)
        ctx.update(
            {
                "no_at_date": True,
                "search_default_on_hand": True,
                "force_restricted_owner_id": self.id,
            }
        )
        return self.env["stock.quant"].with_context(**ctx)._get_quants_action(domain)
