# Copyright 2018 Carlos Dauden - Tecnativa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AgreementDuplicateWizard(models.TransientModel):
    _name = "agreement.duplicate.wizard"
    _description = "Wizard Agreement Duplicate"

    action_type = fields.Selection(
        [("duplicate", "Duplicate agreement"), ("renew", "Renew agreement")],
        default="duplicate",
        string="Action type",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
    )
    start_date = fields.Date(
        string="From Date",
    )
    end_date = fields.Date(string="To Date")

    def action_apply(self):
        Agreement = self.env["agreement"]
        new_agreements = Agreement
        agreements = Agreement.browse(self.env.context["active_ids"])
        for agreement in agreements:
            vals = {"previous_agreement_id": agreement.id}
            if self.partner_id:
                vals["partner_id"] = self.partner_id.id
            if self.start_date:
                vals["start_date"] = self.start_date
            if self.end_date:
                vals["end_date"] = self.end_date
            new_agreements |= agreement.copy(vals)
        if self.action_type == "renew":
            # Finalize origin agreement
            agreements.write(
                {
                    "end_date": self.start_date - relativedelta(days=1),
                    "date_low": fields.Date.today(),
                    "move_type": "B",
                }
            )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "agreement.agreement_action"
        )
        if len(new_agreements) > 0:
            action["domain"] = [("id", "in", new_agreements.ids)]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action
