# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sale_price_unit = fields.Float(readonly=False, inverse="_inverse_sale_price_unit")
    is_sale_price_editable = fields.Boolean(
        string="Is sale price editable",
        compute="_compute_is_sale_price_editable",
    )

    @api.depends("sale_line.qty_invoiced")
    def _compute_is_sale_price_editable(self):
        for record in self:
            record.is_sale_price_editable = (
                record.sale_line and record.sale_line.qty_invoiced == 0.0
            )

    def _inverse_sale_price_unit(self):
        for rec in self:
            rec.sale_line.price_unit = rec.sale_price_unit
