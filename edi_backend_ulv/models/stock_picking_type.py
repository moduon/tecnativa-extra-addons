#  Copyright 2024 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl

from odoo import fields, models


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    # Technical field to allow filter Unilever refund by operation types
    # TT50174
    unilever_refund = fields.Boolean(
        help="Take into account this operation type to "
        "appears in Unilever refunds pending filter"
    )
