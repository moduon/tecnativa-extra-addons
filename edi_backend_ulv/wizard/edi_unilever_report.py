# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class UnileverReportWiz(models.TransientModel):
    _name = "unilever.report.wiz"
    _description = "Wizard to print data requested by Unilever"

    start_date = fields.Date(string="From")
    end_date = fields.Date(string="To")

    def _get_records_to_print(self, report):
        model_report = self.env[report.model_id.model]
        ctx = self.env.context.copy()
        active_ids = ctx.get("active_ids")
        if active_ids and ctx.get("active_model") == "agreement.rebate.settlement":
            domain = [("settlement_id", "in", active_ids)]
        elif report.report_name == "edi_backend_ulv.agreement_pol_settlement":
            domain = [
                ("agreement_type_id", "=", self.env.ref("edi_backend_ulv.POL").id)
            ]
        elif report.report_name == "edi_backend_ulv.invoice_discounts_report":
            domain = [
                ("settlement_id.date_from", ">=", self.start_date),
                ("settlement_id.date_to", "<=", self.end_date),
                ("settlement_id.unilever_settlement_type", "=", "dto_invoice"),
            ]
        elif report.report_name == "edi_backend_ulv.year_bonus_report":
            domain = [
                ("settlement_id.date_from", ">=", self.start_date),
                ("settlement_id.date_to", "<=", self.end_date),
                ("settlement_id.unilever_settlement_type", "=", "bonus"),
            ]
        return model_report.search(domain)

    def print_report(self):
        report = self.env.ref(self.env.context.get("report_ref"))
        recs_to_print = self._get_records_to_print(report)
        if not recs_to_print:
            raise UserError(_("There is not data to print!"))
        form = self.read()[0]
        data = {
            "form": form,
            "doc_ids": recs_to_print.ids,
            "docids": recs_to_print.ids,
            "doc_model": report.model,
            "docs": recs_to_print,
        }
        action = report.report_action(recs_to_print, data=data, config=False)
        return action
