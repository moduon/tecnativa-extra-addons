# Copyright 2022 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    logistic_label_domain = fields.Char(
        related="company_id.logistic_label_domain",
        readonly=False,
    )
    sanitary_registry_logistic_labels = fields.Char(
        string="Sanitary registry for logistic labels",
        related="company_id.sanitary_registry_logistic_labels",
        readonly=False,
    )
    logistic_label_display_lot_barcode = fields.Boolean(
        related="company_id.logistic_label_display_lot_barcode",
        readonly=False,
    )
