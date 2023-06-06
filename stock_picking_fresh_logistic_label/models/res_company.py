# Copyright 2022 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    logistic_label_domain = fields.Char(string="Domain for logistic labels")
    sanitary_registry_logistic_labels = fields.Char(
        string="Sanitary registry for logistic labels"
    )
    logistic_label_display_lot_barcode = fields.Boolean(
        string="Display lots with barcode format"
    )
