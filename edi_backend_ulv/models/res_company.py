#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    unilever_dealer = fields.Char(string="Unilever Dealer", size=10)
    unilever_comunication_code = fields.Char(
        string="Unilever Communication Code", size=5
    )
    no_recount_days_limit = fields.Integer(
        string="No-recount days limit",
    )
    anual_percent_discount_default = fields.Char(string="Default % Anual Discount")
