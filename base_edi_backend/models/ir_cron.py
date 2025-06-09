# Copyright 2023 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl

from odoo import fields, models


class IrCron(models.Model):
    _inherit = "ir.cron"

    edi_backend_id = fields.Many2one(
        comodel_name="edi.backend", string="EDI Backend", ondelete="cascade"
    )
