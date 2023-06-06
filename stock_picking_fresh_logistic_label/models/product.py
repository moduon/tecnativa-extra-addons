# Copyright 2022 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    label_coefficient = fields.Integer(
        string="Division / Coefficient on logistic labels",
        compute="_compute_label_coefficient",
        inverse="_inverse_label_coefficient",
    )

    @api.depends("product_variant_ids", "product_variant_ids.label_coefficient")
    def _compute_label_coefficient(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        )
        for template in unique_variants:
            template.label_coefficient = template.product_variant_ids.label_coefficient
        for template in self - unique_variants:
            template.label_coefficient = 0.0

    def _inverse_label_coefficient(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.label_coefficient = (
                    template.label_coefficient
                )


class ProductProduct(models.Model):
    _inherit = "product.product"

    label_coefficient = fields.Integer(
        string="Division / Coefficient on logistic labels", default=1
    )
