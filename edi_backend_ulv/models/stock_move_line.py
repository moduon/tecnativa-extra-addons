#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # Create index for generate report
    product_id = fields.Many2one(index=True)
    lot_id = fields.Many2one(index=True)
    state = fields.Selection(index=True)
    # TT40508
    # This sequence allow to display detailed operations in the same sequence of
    # ALC file lines
    edi_unilever_sequence_file = fields.Integer(string="ALC Sequence (UL)")
