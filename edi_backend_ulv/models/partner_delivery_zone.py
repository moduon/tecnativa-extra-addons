# Copyright 2019 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PartnerDeliveryZone(models.Model):
    _inherit = "partner.delivery.zone"

    unilever_code = fields.Integer(string="Unilever code")
