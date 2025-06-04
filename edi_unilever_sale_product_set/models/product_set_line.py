# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ProductSet(models.Model):
    _inherit = "product.set.line"

    price_unit = fields.Float(
        string="Unit Price", compute="_compute_price_unit", readonly=False, store=True
    )

    @api.depends("product_id")
    def _compute_price_unit(self):
        pricelist = self.env["product.pricelist"].search([], limit=1)
        for line in self:
            price = line.product_id.with_context(
                pricelist=pricelist.id, uom=line.product_id.uom_id.id, quantity=1.0
            ).price
            line.price_unit = price
