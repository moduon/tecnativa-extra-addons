# Copyright 2018 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    amount_cost_extra = fields.Float(
        string="Extra Amount Cost",
        digits="Product Price",
        groups="product_cost_security.group_product_cost",
        tracking=True,
    )
    standard_price_extra = fields.Float(
        string="Cost Price",
        compute="_compute_standard_price_extra_template",
        search="_search_standard_price_extra",
        digits="Product Price",
        groups="product_cost_extra.group_product_cost_extra",
        compute_sudo=True,
    )

    @api.depends(
        "amount_cost_extra",
        "product_variant_ids",
        "product_variant_ids.standard_price_extra",
    )
    def _compute_standard_price_extra_template(self):
        unique_variants = self.filtered(lambda x: len(x.product_variant_ids) == 1)
        for template in unique_variants:
            template.standard_price_extra = (
                template.standard_price + template.amount_cost_extra
            )
        for template in self - unique_variants:
            template.standard_price_extra = 0.0

    def _search_standard_price_extra(self, operator, value):
        products = self.env["product.product"].search(
            [
                ("standard_price_extra", operator, value),
            ],
            limit=None,
        )
        return [("id", "in", products.mapped("product_tmpl_id").ids)]

    def price_compute(
        self, price_type, uom=None, currency=None, company=None, date=False
    ):
        """The `standard_price_extra` field can only be accessed by the users with
        the proper permission. But any user should be able to get the price of a
        given pricelist no matter which field is based on"""
        if price_type == "standard_price_extra":
            return super(ProductTemplate, self.sudo()).price_compute(
                price_type, uom=uom, currency=currency, company=company, date=date
            )
        return super().price_compute(
            price_type=price_type,
            uom=uom,
            currency=currency,
            company=company,
            date=date,
        )
