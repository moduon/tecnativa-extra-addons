#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    unilever_mrdr_ref = fields.Char(string="Unilever MRDR Ref")
