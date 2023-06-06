# Copyright 2021 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sale_product_security_price_display_raise_button = fields.Boolean(
        related="company_id.sale_product_security_price_display_raise_button",
        readonly=False,
    )
    security_price_rounding_factor = fields.Float(
        related="company_id.security_price_rounding_factor",
        readonly=False,
    )
    allow_custom_defaults_for_security_price = fields.Boolean(
        related="company_id.allow_custom_defaults_for_security_price",
        readonly=False,
    )
    security_price_control_default = fields.Boolean(
        related="company_id.security_price_control_default",
        readonly=False,
    )
    security_price_method_default = fields.Selection(
        [("fixed", "Security Price fixed"), ("percent", "Security Price from percent")],
        related="company_id.security_price_method_default",
        readonly=False,
    )
    value_for_default_security_price = fields.Float(
        related="company_id.value_for_default_security_price",
        readonly=False,
    )
