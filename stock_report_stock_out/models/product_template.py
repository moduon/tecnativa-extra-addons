# Copyright 2024 Sergio Teruel - Tecnativa
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    stock_out_tolerance_percentage = fields.Float(string="Stock Out Tolerance")

    def get_stock_out_tolerance_percentage(self):
        """
        Return tolerance percent for product or category (Or any parent) or form
        config settings
        """
        self.ensure_one()
        if self.stock_out_tolerance_percentage:
            return self.stock_out_tolerance_percentage
        tolerance_categ = self.categ_id.get_stock_out_tolerance_percentage()
        if tolerance_categ:
            return tolerance_categ
        else:
            return self.env.company.stock_out_tolerance_percentage
