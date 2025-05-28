# Copyright 2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    unilever_rappel_group_id = fields.Many2one(
        comodel_name="unilever.rappel.group",
        string="UL rappel group",
    )
    price_unit_signed = fields.Float(string="Price unit signed", readonly=True)
    discount = fields.Float(string="Discount", readonly=True, group_operator="avg")

    def _select(self):
        return (
            super()._select()
            + """
            , template.unilever_rappel_group_id as unilever_rappel_group_id
            , (line.price_unit * line.quantity) * (CASE WHEN move.move_type IN
                ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
            as price_unit_signed, line.discount
        """
        )

    def _group_by(self):
        return (
            super()._group_by()
            + """
            , template.unilever_rappel_group_id
            , line.discount
        """
        )
