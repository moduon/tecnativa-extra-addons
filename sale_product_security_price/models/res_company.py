#  Copyright 2021 Tecnativa - Ernesto Tejeda
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_product_security_price_display_raise_button = fields.Boolean(
        string="Display button on sale order lines to raise price to security price",
        default=True,
    )
    security_price_rounding_factor = fields.Float(
        string="Security price rounding factor",
        default=0.05,
    )
    allow_custom_defaults_for_security_price = fields.Boolean()
    security_price_control_default = fields.Boolean(
        string="Default value for security price control"
    )
    security_price_method_default = fields.Selection(
        [("fixed", "Security Price fixed"), ("percent", "Security Price from percent")],
        default="fixed",
    )
    value_for_default_security_price = fields.Float()
