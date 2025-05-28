# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import api, fields, models


class AgreementSettlementMixin(models.AbstractModel):
    _name = "settlement.mixin"
    _description = "Settlement mixin"

    report_name = ""

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self.report_name)
        docids = docids or data.get("doc_ids")
        docs = (
            self.env[report.model]
            .browse(docids)
            .sorted(
                key=lambda stl: stl.partner_id.unilever_ref
                and stl.partner_id.unilever_ref.isnumeric()
                and int(stl.partner_id.unilever_ref)
                or 99999999
            )
        )
        if data.get("form", False):
            return {
                "doc_ids": docids,
                "data": data,
                "start_date": fields.Date.from_string(data["form"]["start_date"]),
                "end_date": fields.Date.from_string(data["form"]["end_date"]),
                "doc_model": report.model,
                "docs": docs,
                "total_by_subgroup": self._compute_totalized_quantities,
            }
        else:
            return {
                "doc_ids": docids,
                "data": data,
                "doc_model": report.model,
                "docs": docs,
                "total_by_subgroup": self._compute_totalized_quantities,
            }

    def _compute_totalized_quantities(self, docs):
        total_dict = defaultdict(
            lambda: {
                "amount_gross": 0.0,
                "amount_invoiced": 0.0,
                "amount_rebate": 0.0,
                "unilever_contribution_amount": 0.0,
            }
        )
        for doc in docs:
            total_dict[doc.unilever_rappel_group_id.name][
                "amount_gross"
            ] += doc.amount_gross
            total_dict["Total General"]["amount_gross"] += doc.amount_gross
            total_dict[doc.unilever_rappel_group_id.name][
                "amount_invoiced"
            ] += doc.amount_invoiced
            total_dict["Total General"]["amount_invoiced"] += doc.amount_invoiced
            total_dict[doc.unilever_rappel_group_id.name][
                "amount_rebate"
            ] += doc.amount_rebate
            total_dict["Total General"]["amount_rebate"] += doc.amount_rebate
            total_dict[doc.unilever_rappel_group_id.name][
                "unilever_contribution_amount"
            ] += doc.unilever_contribution_amount
            total_dict["Total General"][
                "unilever_contribution_amount"
            ] += doc.unilever_contribution_amount
        return total_dict


class AgreementPolSettlement(models.AbstractModel):
    _inherit = "settlement.mixin"
    report_name = "edi_backend_ulv.agreement_pol_settlement"
    _name = "report.%s" % report_name
    _description = "Unilever agreement POL settlements"


class AgreementDTOSettlement(models.AbstractModel):
    _inherit = "settlement.mixin"
    report_name = "edi_backend_ulv.invoice_discounts_report"
    _name = "report.%s" % report_name
    _description = "Unilever agreement DTO settlements"


class AgreementBonusSettlement(models.AbstractModel):
    _inherit = "settlement.mixin"
    report_name = "edi_backend_ulv.year_bonus_report"
    _name = "report.%s" % report_name
    _description = "Unilever agreement bonus settlements"
