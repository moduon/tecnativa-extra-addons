# Copyright 2021 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ReportRecountPendingFreezers(models.AbstractModel):
    _name = "report.edi_backend_ulv.recount_pending_freezers"
    _description = "Recount-pending Freezers Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        # If data.get("server_action") is True, the report is requested
        # from a server action (invoked from a menu option) and the
        # docids ARE ALREADY CORRECTLY FILTERED, else the it is
        # requested generated from a view of 'Lots/Serial Numbers'
        doc_obj = self.env["stock.production.lot"]
        if data.get("server_action"):
            docs_to_print = doc_obj.browse(data.get("docids", False))
        else:
            docs_to_print = doc_obj.get_recount_pending_freezers(docids)
        data = {
            "doc_ids": docs_to_print.ids,
            "doc_model": "stock.production.lot",
            "docs": docs_to_print,
        }
        return data
