#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class ProductBrand(models.Model):
    _inherit = "product.brand"

    unilever_ref = fields.Char(string="Unilever Ref")
    # Technical field to allow filter Unilever refund by operation types
    # TT50174
    unilever_refund = fields.Boolean(
        help="Take into account this product brand to "
        "appears in Unilever refunds pending filter"
    )
