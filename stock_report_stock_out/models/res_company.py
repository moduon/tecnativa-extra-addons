# Copyright 2020 Sergio Teruel - Tecnativa
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    stock_report_stock_out_recipient_ids = fields.Many2many(
        comodel_name="res.users",
        string="Recipients for stock out summary email",
    )
    stock_report_stock_out_hour = fields.Float(string="Hour to get stock moves")
