# Copyright 2020 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class StockReportStockOut(models.TransientModel):
    _name = "stock.report.stock.out.wiz"
    _description = "Stock report stock out wizard"

    def _default_date_time(self, interval=0):
        """
        Compute date in UTC format
        :param interval:
        :return: Datetime in UTC format
        """
        stock_out_hour = self.env.company.stock_report_stock_out_hour
        hour_str = str(timedelta(hours=stock_out_hour)).zfill(8)
        interval_day = fields.Date.today() - timedelta(days=interval)
        interval_day = f"{fields.Date.to_string(interval_day)} {hour_str}"
        interval_day_time = fields.Datetime.to_datetime(interval_day)
        user_tz = pytz.timezone(self.env.user.tz)
        utc_tz = pytz.timezone("UTC")
        time_utc = (
            user_tz.localize(interval_day_time).astimezone(utc_tz).replace(tzinfo=None)
        )
        return time_utc

    date_from = fields.Datetime(
        string="Date from",
        default=lambda self: self._default_date_time(interval=1),
        required=True,
    )
    date_to = fields.Datetime(
        string="Date to",
        default=lambda self: self._default_date_time(interval=-1),
    )

    @api.model
    def _get_moves_stock_out(self, date_from, date_to=False):
        picking_domain = [
            ("scheduled_date", ">=", self.date_from),
            ("state", "!=", "cancel"),
        ]
        if date_to:
            picking_domain = expression.AND(
                [[("scheduled_date", "<", date_to)], picking_domain]
            )
        pickings = self.env["stock.picking"].search(picking_domain)
        # api model method to be called from abstract report model
        # Changed date_expected to date instead of date_deadline because the second
        # will be False when the picking is created manually, because it hasn't a
        # default that applies the value.
        domain = [
            ("location_dest_id.usage", "=", "customer"),
            ("picking_id", "in", pickings.ids),
            ("date", ">=", date_from),
            "|",
            ("state", "=", "partially_available"),
            "|",
            ("state", "=", "confirmed"),
            "&",
            ("state", "=", "cancel"),
            "|",
            ("picking_id.backorder_id", "!=", False),
            ("sale_line_id.state", "!=", "cancel"),
        ]
        if date_to:
            domain = expression.AND([[("date", "<", date_to)], domain])
        moves_stock_out = self.env["stock.move"].search(domain)
        return moves_stock_out

    def action_open_view_moves(self):
        moves = self._get_moves_stock_out(self.date_from, self.date_to)
        moves_dic = self.env[
            "report.stock_report_stock_out.report_stock_out"
        ]._get_moves_dic(moves)
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        action["domain"] = [
            (
                "id",
                "in",
                (
                    moves_dic["undelivered_moves"]
                    + moves_dic["partial_delivered_moves"]
                ).ids,
            )
        ]
        action["context"] = self.env.context
        return action

    def action_print_report(self):
        moves = self._get_moves_stock_out(self.date_from, self.date_to)
        if not moves:
            raise UserError(_("There is not products stock out"))
        return self.env.ref(
            "stock_report_stock_out.action_report_stock_out"
        ).report_action([], data={"doc_ids": moves.ids})

    def stock_out_summary_send(self):
        moves = self._get_moves_stock_out(self.date_from, self.date_to)
        if not moves:
            raise UserError(_("There is not products stock out"))
        _logger.info(f"Stock report out: From {self.date_from} To {self.date_to}")
        template = self.env.ref("stock_report_stock_out.email_template_stock_out")
        company = self.env.company
        recipients = company.stock_report_stock_out_recipient_ids.mapped("partner_id")
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                lang=self.env.user.lang,
                default_composition_mode="mass_mail",
                default_notify=True,
                default_model=self._name,
                default_template_id=template.id,
                active_ids=self.ids,
                default_partner_ids=recipients.ids,
                doc_ids=moves.ids,
            )
            .create({})
        )
        values = composer._onchange_template_id(
            template.id, "mass_mail", self._name, self.id
        )["value"]
        composer.write(values)
        composer._action_send_mail()
        return True
