# Copyright 20121 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    no_recount_days_limit = fields.Integer(
        related="company_id.no_recount_days_limit",
        readonly=False,
    )
    anual_percent_discount_default = fields.Char(
        related="company_id.anual_percent_discount_default",
        readonly=False,
    )
