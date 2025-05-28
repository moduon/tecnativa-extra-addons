# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class AgreementRebateSettlement(models.Model):
    _inherit = "agreement.rebate.settlement"

    unilever_settlement_type = fields.Selection(
        [("dto_invoice", "Dto invoice"), ("bonus", "Bonus")]
    )

    def action_show_agreement(self):
        agreements = self.line_ids.mapped("agreement_id")
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "agreement.agreement_action"
        )
        if len(agreements) == 1:
            form = self.env.ref("edi_backend_ulv.agreement_form")
            action["views"] = [(form.id, "form")]
            action["res_id"] = agreements.id
        else:
            action["domain"] = [("id", "in", agreements.ids)]
        return action


class AgreementRebateSettlementLine(models.Model):
    _inherit = ["agreement.rebate.settlement.line", "edi.backend.mixin"]
    _name = "agreement.rebate.settlement.line"

    unilever_participation_percent = fields.Float(
        string="% Unilever Participation",
        readonly=True,
    )
    unilever_contribution_amount = fields.Float(
        string="Unilever contribution amount",
        readonly=True,
    )
    unilever_rappel_group_id = fields.Many2one(
        comodel_name="unilever.rappel.group",
        string="UL rappel group",
        ondelete="restrict",
        readonly=True,
    )
    unilever_percent_total = fields.Float(
        string="% Total",
        compute="_compute_unilever_percent_total",
        store=True,
    )

    @api.depends("settlement_id.amount_invoiced", "amount_invoiced")
    def _compute_unilever_percent_total(self):
        minimal_total_percent = self.env.context.get("minimal_total_percent", 0.0)
        for line in self:
            line.unilever_percent_total = (
                (line.amount_invoiced / line.settlement_id.amount_invoiced * 100)
                if line.settlement_id.amount_invoiced
                else 0.0
            )
            if (
                minimal_total_percent
                and line.unilever_percent_total < minimal_total_percent
            ):
                line.unilever_state = "cancelled"

    def _prepare_invoice_line(self, invoice_vals):
        vals = super()._prepare_invoice_line(invoice_vals)
        if self.settlement_id.unilever_settlement_type in [
            "dto_invoice",
            "bonus",
        ]:
            vals["name"] = _(
                "{}\n{}% de rappel sobre consumo de {} €\nPeriodo: {} - {}".format(
                    self.unilever_rappel_group_id.name,
                    self.percent,
                    self.amount_invoiced,
                    self.settlement_id.date_from,
                    self.settlement_id.date_to,
                )
            )
        return vals
