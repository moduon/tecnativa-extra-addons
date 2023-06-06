# Copyright 2018 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from math import ceil

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_default_security_price_method(self):
        if (
            not self.env.company.allow_custom_defaults_for_security_price
            or not self.env.company.security_price_method_default
        ):
            return "fixed"
        return self.env.company.security_price_method_default

    def _get_default_security_price_percent(self):
        if (
            not self.env.company.allow_custom_defaults_for_security_price
            or self.env.company.security_price_method_default != "percent"
        ):
            return 0.0
        return self.env.company.value_for_default_security_price

    def _get_default_security_price_control(self):
        if (
            not self.env.company.allow_custom_defaults_for_security_price
            or not self.env.company.security_price_control_default
        ):
            return False
        return True

    security_price = fields.Float(
        string="Security price",
        digits="Product Price",
        tracking=True,
        compute="_compute_security_price",
        store=True,
        readonly=False,
    )
    security_price_control = fields.Boolean(
        string="Security price control",
        default=_get_default_security_price_control,
        groups="product_cost_security.group_product_cost",
    )
    security_price_margin = fields.Float(
        string="(%) Security price margin",
        groups="product_cost_security.group_product_cost",
        compute="_compute_security_price_margin",
        store=True,
    )
    # No añado grupo porque es necesario para hacer el campo security_price readonly
    # en la vista de producto.
    security_price_method = fields.Selection(
        [("fixed", "Security Price fixed"), ("percent", "Security Price from percent")],
        string="Method for Security Price Computation",
        default=_get_default_security_price_method,
    )
    security_price_percent = fields.Float(
        string="Security price percent",
        groups="product_cost_security.group_product_cost",
        default=_get_default_security_price_percent,
    )

    @api.depends(lambda x: x._get_security_price_depends())
    def _compute_security_price(self):
        for product in self:
            if product.security_price_method == "percent":
                product.security_price = (
                    ceil(
                        (
                            product[self._get_standard_price_field()]
                            / (1 - product.security_price_percent / 100)
                        )
                        / self.env.company.security_price_rounding_factor
                    )
                    * self.env.company.security_price_rounding_factor
                )
            else:
                product.security_price = product._origin.security_price

    @api.model
    def _get_security_price_depends(self):
        return [
            "security_price_method",
            self._get_standard_price_field(),
            "security_price_percent",
        ]

    def get_security_price_template(self):
        return self.env["product.security.price.template"].search(
            [
                ("amount_from", "<=", self.standard_price),
                ("amount_to", ">=", self.standard_price),
                "|",
                ("company_id", "=", self.env.company.id),
                ("company_id", "=", False),
            ],
            order="amount_from",
            limit=1,
        )

    def action_security_price_from_template(self):
        for template in self.filtered(lambda t: not t.security_price):
            security_tmpl = template.get_security_price_template()
            if security_tmpl:
                if security_tmpl.security_price_method == "fixed":
                    template.security_price_method = "fixed"
                    template.security_price = (
                        template[self._get_standard_price_field()]
                        + security_tmpl.security_price
                    )
                elif security_tmpl.security_price_method == "percent":
                    template.security_price_method = "percent"
                    template.security_price_percent = (
                        security_tmpl.security_price_percent
                    )

    @api.depends(lambda x: x._get_security_price_margin_depends())
    def _compute_security_price_margin(self):
        for template in self:
            if not (
                template[self._get_standard_price_field()] and template.security_price
            ):
                template.security_price_margin = 0.0
            else:
                template.security_price_margin = (
                    (
                        template.security_price
                        - template[self._get_standard_price_field()]
                    )
                    / template.security_price
                    * 100
                )

    @api.model
    def _get_security_price_margin_depends(self):
        return ["security_price", self._get_standard_price_field()]

    def _get_standard_price_field(self):
        return "standard_price"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_security_price_template(self):
        return self.env["product.security.price.template"].search(
            [
                ("amount_from", "<=", self.standard_price),
                ("amount_to", ">=", self.standard_price),
                "|",
                ("company_id", "=", self.env.company.id),
                ("company_id", "=", False),
            ],
            order="amount_from",
            limit=1,
        )

    def action_security_price_from_template(self):
        for product in self.filtered(lambda t: not t.security_price):
            security_tmpl = product.get_security_price_template()
            if security_tmpl:
                if security_tmpl.security_price_method == "fixed":
                    product.security_price_method = "fixed"
                    product.security_price = (
                        product[self._get_standard_price_field()]
                        + security_tmpl.security_price
                    )
                elif security_tmpl.security_price_method == "percent":
                    product.security_price_method = "percent"
                    product.security_price_percent = (
                        security_tmpl.security_price_percent
                    )
