# Copyright 2018 Sergio Teruel - Tecnativa <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ProductSecurityPriceTemplate(models.Model):
    _name = "product.security.price.template"
    _description = "Product security price from company"
    _order = "amount_from"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    amount_from = fields.Float(
        string="Amount from",
        digits="Product Price",
    )
    amount_to = fields.Float(
        string="Amount to",
        digits="Product Price",
    )
    security_price = fields.Float(
        string="Amount extra",
        digits="Security Price",
    )
    security_price_method = fields.Selection(
        [("fixed", "Security Price fixed"), ("percent", "Security Price from percent")],
        string="Method for Security Price Computation",
        default="fixed",
        required=True,
    )
    security_price_percent = fields.Float(string="Security price percent")

    @api.onchange("security_price_method")
    def _onchange_security_price_method(self):
        self.security_price = 0
        self.security_price_percent = 0
