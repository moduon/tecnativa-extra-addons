# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class AgreementType(models.Model):
    _inherit = "agreement.type"

    code = fields.Char(string="Code")
