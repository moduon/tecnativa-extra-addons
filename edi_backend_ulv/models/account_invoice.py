#  Copyright 2019 Tecnativa - Sergio Teruel
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


# TODO: Migration script
class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    amount_tourism_discount = fields.Float(
        compute="_compute_amount_discount",
        string="Amount Tourism Discount",
    )
    amount_unilever_participation = fields.Float(
        compute="_compute_amount_discount",
        string="Amount Unilever Participation",
    )
    amount_dealer_participation = fields.Float(
        compute="_compute_amount_discount",
        string="Amount Dealer Participation",
    )
    unilever_agreement_id = fields.Many2one(
        comodel_name="agreement",
        compute="_compute_unilever_agreement_id",
    )
    unilever_communication_history_ids = fields.Many2many(
        comodel_name="edi.backend.communication.history",
        relation="account_move_line_backend_communication_history_rel",
        column1="invoice_line_id",
        column2="communication_history_id",
    )

    def _compute_unilever_agreement_id(self):
        for line in self:
            line.unilever_agreement_id = line.sale_line_ids.mapped(
                "unilever_agreement_id"
            )[:1]

    def _compute_amount_discount(self):
        for line in self:
            agreement = line.unilever_agreement_id
            line.amount_tourism_discount = 0.0
            if agreement.agreement_type == "POL":
                line.amount_tourism_discount = line.quantity * (
                    line.price_unit - agreement.agreement_price
                )
            else:
                amount_dto = line.price_unit * line.quantity - line.price_subtotal
                unilever_participation = amount_dto * (
                    agreement.unilever_participation_percent / 100
                )
                line.amount_unilever_participation = unilever_participation
                line.amount_dealer_participation = amount_dto - unilever_participation
