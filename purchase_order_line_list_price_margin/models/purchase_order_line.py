# Copyright 2021 Tecnativa - Carlos Dauden
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    list_price = fields.Float(string="List price", related="product_id.list_price")
    list_price_margin = fields.Float(
        string="Margin (%)",
        compute="_compute_list_price_margin",
        compute_sudo=True,
        help="(list_price - (price_unit + amount_cost extra)) / list_price",
    )

    @api.depends("price_unit", "product_id.list_price", "product_id.amount_cost_extra")
    def _compute_list_price_margin(self):
        for line in self:
            list_price = line.product_id.list_price
            line.list_price_margin = (
                (list_price - (line.price_unit + line.product_id.amount_cost_extra))
                / list_price
                * 100
                if list_price
                else 0.0
            )
