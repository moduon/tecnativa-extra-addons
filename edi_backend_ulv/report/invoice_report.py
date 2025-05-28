# Copyright 2019 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    unilever_rappel_group_id = fields.Many2one(
        comodel_name="unilever.rappel.group",
        string="UL rappel group",
    )

    def _select(self):
        return (
            super()._select()
            + """
            , sub.unilever_rappel_group_id as unilever_rappel_group_id
        """
        )

    def _sub_select(self):
        return (
            super()._sub_select()
            + """
            , pt.unilever_rappel_group_id as unilever_rappel_group_id
        """
        )

    def _group_by(self):
        return (
            super()._group_by()
            + """
            , pt.unilever_rappel_group_id
        """
        )
