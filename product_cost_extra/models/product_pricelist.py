# Copyright 2020 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist.item"

    base = fields.Selection(
        selection_add=[("standard_price_extra", "Prices based on extra cost")],
        ondelete={"standard_price_extra": "set standard_price"},
    )
    margin_percent = fields.Float(
        string="Margin (%)",
        groups="product_cost_security.group_product_cost",
        digits="Account",
        compute="_compute_margin_percent",
        store=True,
    )

    @api.depends(
        "fixed_price",
        "percent_price",
        "product_tmpl_id.list_price",
        "product_id.list_price",
        "product_tmpl_id.standard_price_extra",
        "product_id.standard_price_extra",
        "price_discount",
        "compute_price",
        "base",
        "base_pricelist_id",
        "price_surcharge",
    )
    def _compute_margin_percent(self):
        self._set_price_margin()

    def _get_price_margin(self, sale_price, cost_price):
        return (sale_price - cost_price) / (sale_price or 1) * 100

    def _set_price_margin(self):
        for item in self:
            product = item.product_id or item.product_tmpl_id.product_variant_id
            if not product:
                item.margin_percent = 0.0
                continue
            margin_percent = 0.0
            if item.fixed_price:
                price = item.fixed_price
            elif item.percent_price:
                price = product.list_price - (
                    product.list_price * (item.percent_price / 100)
                )
            elif item.base_pricelist_id:
                price = item.base_pricelist_id._compute_price_rule(
                    [(product, 1, 0)], fields.Date.today()
                )[product.id][0]
                price = (
                    price - (price * (item.price_discount / 100)) + item.price_surcharge
                ) or 0.0
            else:
                base = item.base
                if base == "pricelist" and not item.base_pricelist_id:
                    base = "list_price"
                price = product.price_compute(base)[product.id]
                price = (
                    price - (price * (item.price_discount / 100)) + item.price_surcharge
                ) or 0.0
            if price:
                margin_percent = self._get_price_margin(
                    price, product.standard_price_extra
                )
            item.margin_percent = margin_percent
