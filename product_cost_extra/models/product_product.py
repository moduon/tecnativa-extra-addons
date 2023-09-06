# Copyright 2018 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price_extra = fields.Float(
        string="Cost Price",
        compute="_compute_standard_price_extra",
        digits="Product Price",
        groups="product_cost_extra.group_product_cost_extra",
        store=True,
    )

    @api.depends("standard_price", "product_tmpl_id.amount_cost_extra")
    def _compute_standard_price_extra(self):
        for product in self:
            product.standard_price_extra = (
                product.standard_price + product.amount_cost_extra
            )

    def price_compute(
        self, price_type, uom=None, currency=None, company=None, date=False
    ):
        """The `standard_price_extra` field can only be accessed by the users with
        the proper permission. But any user should be able to get the price of a
        given pricelist no matter which field is based on"""
        if price_type == "standard_price_extra":
            return super(ProductProduct, self.sudo()).price_compute(
                price_type, uom=uom, currency=currency, company=company, date=date
            )
        return super().price_compute(
            price_type=price_type,
            uom=uom,
            currency=currency,
            company=company,
            date=date,
        )
