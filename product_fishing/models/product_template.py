# Copyright 2023 Tecnativa - Stefan Ungureanu
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    harvesting_method_ids = fields.Many2many(
        comodel_name="product.attribute.value",
        compute="_compute_harvesting_method_ids",
    )
    presentation_ids = fields.Many2many(
        comodel_name="product.attribute.value",
        compute="_compute_product_presentation_ids",
    )
    gamma_ids = fields.Many2many(
        comodel_name="product.attribute.value",
        compute="_compute_gamma_ids",
    )
    allergens_ids = fields.Many2many(
        comodel_name="product.attribute.value", compute="_compute_allergens_ids"
    )
    production_method_ids = fields.Many2many(
        comodel_name="product.attribute.value", compute="_compute_production_method_ids"
    )
    scientific_name_ids = fields.Many2many(
        comodel_name="product.attribute.value", compute="_compute_scientific_name_ids"
    )

    preservation_condition_ids = fields.Many2many(
        comodel_name="product.attribute.value",
        compute="_compute_preservation_condition_ids",
    )
    origin_country_ids = fields.Many2many(
        comodel_name="product.attribute.value",
        compute="_compute_origin_country_ids",
    )

    def _set_attribute_values(self, attribute_ref, field_name):
        """
        Helper method to retrieve the harvesting method from product attributes
        """
        attribute = self.env.ref(attribute_ref)
        ptal_obj = self.env["product.template.attribute.line"]
        attribute_lines = ptal_obj.search(
            [("product_tmpl_id", "in", self.ids), ("attribute_id", "=", attribute.id)]
        )
        for template in self:
            template[field_name] = attribute_lines.filtered(
                lambda att_line: att_line.product_tmpl_id == template
            ).value_ids

    def _compute_harvesting_method_ids(self):
        self._set_attribute_values(
            "product_fishing.harvesting_method_attribute", "harvesting_method_ids"
        )

    def _compute_product_presentation_ids(self):
        self._set_attribute_values(
            "product_fishing.presentation_attribute", "presentation_ids"
        )

    def _compute_gamma_ids(self):
        self._set_attribute_values(
            "product_fishing.product_gamma_attribute", "gamma_ids"
        )

    def _compute_allergens_ids(self):
        self._set_attribute_values(
            "product_fishing.product_allergens_attribute", "allergens_ids"
        )

    def _compute_production_method_ids(self):
        self._set_attribute_values(
            "product_fishing.product_production_method_attribute",
            "production_method_ids",
        )

    def _compute_preservation_condition_ids(self):
        self._set_attribute_values(
            "product_fishing.product_preservation_condition_attribute",
            "preservation_condition_ids",
        )

    def _compute_origin_country_ids(self):
        self._set_attribute_values(
            "product_fishing.product_origin_country_attribute",
            "origin_country_ids",
        )

    def _compute_scientific_name_ids(self):
        self._set_attribute_values(
            "product_fishing.scientific_name",
            "scientific_name_ids",
        )
