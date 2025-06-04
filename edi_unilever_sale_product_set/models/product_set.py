# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ProductSet(models.Model):
    _inherit = "product.set"

    is_ul_fill = fields.Boolean(
        string="Fill operation",
        default="True",
    )
