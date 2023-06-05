# Copyright 2020 Sergio Teruel - Tecnativa
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    stock_report_stock_out_recipient_ids = fields.Many2many(
        related="company_id.stock_report_stock_out_recipient_ids", readonly=False
    )
    stock_report_stock_out_hour = fields.Float(
        related="company_id.stock_report_stock_out_hour", readonly=False
    )
