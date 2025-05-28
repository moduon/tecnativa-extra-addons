# Copyright 2020 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AgreementGiraMixin(models.AbstractModel):
    _name = "agreement.gira.mixin"
    _description = "Agreement gira mixin"

    report_name = ""

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env["ir.actions.report"]._get_report_from_name(self.report_name)
        docids = docids or data.get("doc_ids")
        docs = self.env[report.model].browse(docids)
        return {
            "doc_ids": docids,
            "data": data,
            "doc_model": report.model,
            "docs": docs,
            "line_values": self._compute_line_values,
        }

    def _compute_line_values(self, agreement=None, condition_line=None):
        pass

    def _get_invoice_domain(self, agreement, product):
        domain = [
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("partner_id", "=", agreement.partner_id.id),
            ("product_id", "=", product.id),
            ("invoice_date", ">=", agreement.start_date),
        ]
        if agreement.end_date:
            domain.append(("invoice_date", "<=", agreement.end_date))
        return domain

    def _get_gira_vals(self, invoice_ids, agreement, condition_line):
        quantity = sum(invoice_ids.mapped("quantity"))
        pvp_value = sum(invoice_ids.mapped("price_unit_signed"))
        gira_value = sum(invoice_ids.mapped("price_subtotal"))
        unilever_contrib = gira_value * agreement.unilever_participation_percent / 100
        return {
            "quantity": quantity,
            "pvp_value": pvp_value,
            "gira_value": gira_value,
            "contrib_percent": agreement.unilever_participation_percent,
            "unilever_contrib": unilever_contrib,
        }


class AgreementGiraSummary(models.AbstractModel):
    _inherit = "agreement.gira.mixin"
    report_name = "edi_backend_ulv.gira_summary_report"
    _name = "report.%s" % report_name
    _description = "Unilever GIRA summary"

    def _compute_line_values(self, agreement=None, condition_line=None):
        super()._compute_line_values(agreement=agreement, condition_line=condition_line)
        if agreement and condition_line:
            invoice_ids = self.env["account.invoice.report"].search(
                self._get_invoice_domain(agreement, condition_line.product_id)
            )
            return self._get_gira_vals(invoice_ids, agreement, condition_line)


class AgreementGiraDeatiled(models.AbstractModel):
    _inherit = "agreement.gira.mixin"
    report_name = "edi_backend_ulv.gira_detailed_report"
    _name = "report.%s" % report_name
    _description = "Unilever GIRA detailed report"

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data=data)
        res["datetime_print"] = fields.Datetime().now()
        return res

    def _compute_line_values(self, agreement=None, condition_line=None):
        super()._compute_line_values(agreement=agreement, condition_line=condition_line)
        if condition_line:
            agreements = self.env["agreement"].search(
                [
                    (
                        "agreement_condition_id",
                        "=",
                        condition_line.agreement_condition_id.id,
                    )
                ]
            )
            vals_per_invoice = []
            for agreement in agreements:
                invoice_ids = self.env["account.invoice.report"].search(
                    self._get_invoice_domain(agreement, condition_line.product_id)
                )
                for invoice in invoice_ids:
                    res = self._get_gira_vals(invoice, agreement, condition_line)
                    # res["se"] = "??"
                    res["invoice"] = invoice.name
                    res["date"] = invoice.invoice_date
                    res["client_ref"] = invoice.partner_shipping_id.unilever_ref
                    res["client_name"] = invoice.partner_shipping_id.name
                    vals_per_invoice.append(res)
            return vals_per_invoice
