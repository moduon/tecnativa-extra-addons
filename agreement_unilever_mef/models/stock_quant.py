# Copyright 2022 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    # TT36757 and TT37160
    @api.constrains("quantity")
    def check_quantity(self):
        internal_quants = self.filtered(lambda q: q.location_id.usage == "internal")
        return super(StockQuant, internal_quants).check_quantity()
