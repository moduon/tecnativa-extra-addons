#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl
from odoo import models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    def do_scrap(self):
        res = super().do_scrap()
        scraps_mef = self.filtered("product_id.categ_id.is_unilever_mef")
        scraps_mef.mapped("lot_id").write({"unilever_low_reason": "D"})
        return res
