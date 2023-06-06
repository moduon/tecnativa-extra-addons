# Copyright 2022 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, time

import pytz

from odoo import fields, models


class PurchaseStockAccountInvoicePendingWizard(models.TransientModel):
    _name = "purchase.stock.account.invoice.pending.wizard"
    _description = "Wizard purchase stock account invoice pending"

    date_from = fields.Date()
    date_to = fields.Date(required=True)

    def _get_records_to_print(self):
        sql = """
            SELECT sub.order_id, sub.id, sub.moves_qty, sub.invoiced_qty
            FROM
            (SELECT
              pol.order_id, pol.id,
              COALESCE((SELECT
                SUM(CASE
                  WHEN source_location.usage = 'supplier' AND
                       dest_location.usage = 'internal'
                    THEN 1
                  WHEN source_location.usage = 'internal' AND
                       dest_location.usage = 'supplier' AND sm.to_refund
                    THEN -1
                  ELSE 0
                END * sm.product_uom_qty)
              FROM stock_move sm
                JOIN stock_location source_location ON sm.location_id = source_location.id
                JOIN stock_location dest_location ON sm.location_dest_id = dest_location.id
              WHERE sm.purchase_line_id = pol.id AND sm.state = 'done' AND sm.date <= %s
              ), 0.0) as moves_qty,
              COALESCE((SELECT SUM(CASE
                  WHEN am.move_type = 'in_invoice'
                    THEN 1
                  WHEN am.move_type = 'in_refund'
                    THEN -1
                  ELSE 0 END * aml.quantity)
                  FROM account_move_line aml
                    LEFT JOIN account_move am ON am.id = aml.move_id
                  WHERE aml.purchase_line_id = pol.id AND aml.parent_state = 'posted'
                   AND aml.date <= %s
                  ), 0.0) as invoiced_qty
            FROM purchase_order_line pol
              JOIN product_product pp ON pp.id = pol.product_id
              JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE pol.state = 'purchase' AND pol.company_id IN %s
                AND pt.purchase_method = 'receive'
            ) as sub
            WHERE sub.moves_qty <> sub.invoiced_qty
        """
        # Get day with max time in UTC
        datetime_to = datetime.combine(self.date_to, time.max)
        user_tz = pytz.timezone(self.env.user.tz)
        datetime_to_utc = user_tz.localize(datetime_to).astimezone(pytz.timezone("UTC"))
        datetime_to_str = fields.Datetime.to_string(datetime_to_utc)
        date_to_str = fields.Date.to_string(self.date_to)
        self.env.cr.execute(
            sql, (datetime_to_str, date_to_str, tuple(self.env.companies.ids))
        )
        return self.env.cr.dictfetchall()

    def print_report(self):
        report = self.env.ref(
            "purchase_stock_account_invoice_pending.purchase_pending_report"
        )
        recs_to_print = self._get_records_to_print()
        form = self.read()[0]
        data = {
            "form": form,
            "doc_model": "purchase.order",
            "recs_to_print": recs_to_print,
        }
        return report.report_action(recs_to_print, data=data, config=False)
