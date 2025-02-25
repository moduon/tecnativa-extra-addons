# Copyright 2024 Sergio Teruel - Tecnativa
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    stock_out_tolerance_percentage = fields.Float(string="Stock Out Tolerance (%)")

    def get_stock_out_tolerance_percentage(self):
        self.ensure_one()
        if self.stock_out_tolerance_percentage:
            return self.stock_out_tolerance_percentage
        elif self.parent_id:
            return self.parent_id.get_stock_out_tolerance_percentage()
        else:
            return 0.0
