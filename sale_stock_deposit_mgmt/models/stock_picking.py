# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockPicking(models.Model):

    _inherit = "stock.picking"

    product_owner_ids = fields.Many2many(
        comodel_name="product.product", compute="_compute_product_owner_ids"
    )

    @api.depends("partner_id", "owner_id")
    def _compute_product_owner_ids(self):
        self.product_owner_ids = self.env["product.product"]
        if self.env.context.get("deposit_picking_mgmt"):
            for picking in self.filtered("owner_id"):
                quants = self.env["stock.quant"].search(
                    [
                        ("owner_id", "=", picking.owner_id.id),
                        ("quantity", ">", 0.0),
                    ]
                )
                picking.product_owner_ids = quants.mapped("product_id")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("deposit_picking_mgmt"):
            res["picking_type_id"] = (
                self.env["stock.picking.type"]
                .search([("owner_restriction", "=", "picking_partner")], limit=1)
                .id
            )
        return res

    @api.onchange("picking_type_id", "partner_id")
    def _onchange_picking_type(self):
        res = super(StockPicking, self)._onchange_picking_type() or {}
        if self.env.context.get("deposit_picking_mgmt"):
            self.owner_id = self.partner_id
        return res
